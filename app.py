#!/usr/bin/env python3
"""
CEI Web PDF Signer - Web-based PDF signing using Romanian CEI
Run this server and access via browser at http://localhost:5000
"""

import os
import sys
import base64
import tempfile
import hashlib
import subprocess
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# PKCS#11 imports
try:
    import PyKCS11
    from PyKCS11 import *
    PKCS11_AVAILABLE = True
except ImportError:
    PKCS11_AVAILABLE = False
    print("Warning: PyKCS11 not installed. Install with: pip install PyKCS11")

# PDF signing imports - using pyHanko for proper PKCS#11 ECDSA support
try:
    from pyhanko.sign import signers, fields
    from pyhanko.sign.general import SigningError
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko_certvalidator import ValidationContext
    from pyhanko.stamp import TextStampStyle
    from pyhanko.pdf_utils.text import TextBoxStyle
    from pyhanko.pdf_utils.content import RawContent
    import pkcs11
    from pkcs11 import Mechanism
    PYHANKO_AVAILABLE = True
except ImportError:
    PYHANKO_AVAILABLE = False
    print("Warning: pyhanko not installed. Install with: pip install pyhanko 'pyhanko[pkcs11]'")

# Handle bundled app paths (py2app)
if getattr(sys, 'frozen', False):
    # Running as a bundled app
    bundle_dir = os.path.dirname(sys.executable)
    resources_dir = os.path.join(os.path.dirname(bundle_dir), 'Resources')
    template_folder = os.path.join(resources_dir, 'templates')
else:
    # Running as script
    template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

app = Flask(__name__, template_folder=template_folder)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Default PKCS#11 library for Romanian CEI
DEFAULT_PKCS11_LIB = "/Library/Application Support/com.idemia.idplug/lib/libidplug-pkcs11.2.7.0.dylib"

# Global state
pkcs11_lib = None
pkcs11_session = None


def get_pkcs11_lib_path(custom_path=None):
    """Get PKCS#11 library path - uses custom path if provided, otherwise env var or default"""
    if custom_path and custom_path.strip():
        return custom_path.strip()
    return os.environ.get('PKCS11_LIB', DEFAULT_PKCS11_LIB)


def kill_ctkd():
    """Kill CryptoTokenKit daemon to release smart card reader.
    macOS CTK grabs exclusive PC/SC access on card insertion,
    blocking PKCS#11 access. Killing it forces release."""
    for proc in ('ctkd', 'ctkahp'):
        try:
            subprocess.run(['pkill', '-9', proc],
                           capture_output=True, timeout=5)
        except Exception:
            pass
    # Give PC/SC a moment to reclaim the reader
    time.sleep(0.5)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Check system status"""
    lib_path = get_pkcs11_lib_path()
    return jsonify({
        'pkcs11_available': PKCS11_AVAILABLE,
        'pyhanko_available': PYHANKO_AVAILABLE,
        'pkcs11_lib_path': lib_path,
        'pkcs11_lib_exists': os.path.exists(lib_path)
    })


@app.route('/api/slots')
def api_slots():
    """Detect available smart card slots"""
    if not PKCS11_AVAILABLE:
        return jsonify({'slots': [], 'error': 'PyKCS11 not installed'})

    # Get custom path from query string if provided
    custom_path = request.args.get('pkcs11_path')
    lib_path = get_pkcs11_lib_path(custom_path)
    if not os.path.exists(lib_path):
        return jsonify({'slots': [], 'error': f'PKCS11 library not found at: {lib_path}'})

    last_error = None
    for attempt in range(2):
        try:
            if attempt > 0:
                # First attempt failed — kill CryptoTokenKit and retry
                kill_ctkd()

            lib = PyKCS11.PyKCS11Lib()
            lib.load(lib_path)

            # Get slots with tokens present (card inserted)
            slots = lib.getSlotList(tokenPresent=True)

            if not slots:
                return jsonify({'slots': [], 'error': 'No smart card detected'})

            slot_info = []
            for slot_id in slots:
                try:
                    token_info = lib.getTokenInfo(slot_id)
                    slot_info.append({
                        'id': slot_id,
                        'label': token_info.label.strip(),
                        'model': token_info.model.strip(),
                        'manufacturer': token_info.manufacturerID.strip(),
                    })
                except:
                    slot_info.append({
                        'id': slot_id,
                        'label': f'Slot {slot_id}',
                        'model': 'Unknown',
                        'manufacturer': 'Unknown',
                    })

            return jsonify({'slots': slot_info})

        except PyKCS11.PyKCS11Error as e:
            last_error = f'Smart card error: {str(e)}'
        except Exception as e:
            last_error = f'Error: {str(e)}'

    return jsonify({'slots': [], 'error': last_error})


@app.route('/api/certificate', methods=['POST'])
def api_get_certificate():
    """Get certificate from smart card"""
    if not PKCS11_AVAILABLE:
        return jsonify({'error': 'PyKCS11 not installed'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    slot_id = int(data.get('slot', 2))
    pin = str(data.get('pin', '')).strip()

    if not pin:
        return jsonify({'error': 'PIN required'}), 400

    try:
        custom_path = data.get('pkcs11_path')
        lib_path = get_pkcs11_lib_path(custom_path)
        lib = PyKCS11.PyKCS11Lib()
        lib.load(lib_path)

        # Check available slots first
        available_slots = lib.getSlotList(tokenPresent=True)
        if slot_id not in available_slots:
            return jsonify({'error': f'Slot {slot_id} not available. Available slots: {available_slots}. Please click "Detect Smart Card" again.'}), 400

        session = lib.openSession(slot_id, CKF_SERIAL_SESSION | CKF_RW_SESSION)
        session.login(pin)
        
        # Find certificates
        certs = session.findObjects([(CKA_CLASS, CKO_CERTIFICATE)])
        
        cert_info = []
        for cert in certs:
            attrs = session.getAttributeValue(cert, [CKA_VALUE, CKA_LABEL])
            cert_der = bytes(attrs[0])
            # Handle label - might be string, bytes, or list of ints depending on PyKCS11 version
            raw_label = attrs[1]
            if not raw_label:
                label = 'Unknown'
            elif isinstance(raw_label, str):
                label = raw_label
            elif isinstance(raw_label, (bytes, bytearray)):
                label = raw_label.decode('utf-8', errors='replace')
            elif isinstance(raw_label, (list, tuple)) and raw_label and isinstance(raw_label[0], int):
                label = ''.join(chr(c) for c in raw_label)
            else:
                label = str(raw_label)
            
            # Parse certificate if cryptography is available
            try:
                from cryptography import x509
                from cryptography.hazmat.backends import default_backend
                cert_obj = x509.load_der_x509_certificate(cert_der, default_backend())
                subject = cert_obj.subject.rfc4514_string()
                issuer = cert_obj.issuer.rfc4514_string()
                not_after = cert_obj.not_valid_after_utc.isoformat()
                
                cert_info.append({
                    'label': label,
                    'subject': subject,
                    'issuer': issuer,
                    'valid_until': not_after,
                    'der_base64': base64.b64encode(cert_der).decode('ascii')
                })
            except:
                cert_info.append({
                    'label': label,
                    'der_base64': base64.b64encode(cert_der).decode('ascii')
                })
        
        session.logout()
        session.closeSession()
        
        return jsonify({'certificates': cert_info})
    
    except PyKCS11.PyKCS11Error as e:
        error_msg = str(e)
        if 'CKR_PIN_INCORRECT' in error_msg:
            return jsonify({'error': 'Incorrect PIN. Please check your PIN and try again.'}), 401
        if 'CKR_PIN_LOCKED' in error_msg:
            return jsonify({'error': 'PIN is locked. Too many incorrect attempts.'}), 401
        if 'CKR_TOKEN_NOT_PRESENT' in error_msg:
            return jsonify({'error': 'Smart card not detected. Please insert your CEI card.'}), 500
        if 'CKR_SLOT_ID_INVALID' in error_msg:
            return jsonify({'error': f'Invalid slot {slot_id}. Please click "Detect Smart Card" and select the correct slot.'}), 500
        if 'CKR_USER_NOT_LOGGED_IN' in error_msg:
            return jsonify({'error': 'Session expired. Please try again.'}), 500
        return jsonify({'error': f'Smart card error: {error_msg}'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error: {str(e)}'}), 500


@app.route('/api/sign', methods=['POST'])
def api_sign_pdf():
    """Sign a PDF document using pyHanko with PKCS#11"""
    if not PYHANKO_AVAILABLE:
        return jsonify({'error': 'pyHanko not installed'}), 500

    # Get form data
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    pdf_file = request.files['pdf']
    slot_id = int(request.form.get('slot', 2))
    pin = str(request.form.get('pin', '')).strip()
    reason = request.form.get('reason', 'Document signed with Romanian CEI')
    location = request.form.get('location', 'Romania')
    contact = request.form.get('contact', '')

    # Parse signature boxes from JSON
    import json
    signature_boxes_json = request.form.get('signature_boxes', '[]')
    try:
        signature_boxes = json.loads(signature_boxes_json)
    except:
        signature_boxes = []

    # Use first signature box, or default if none provided
    if signature_boxes:
        box = signature_boxes[0]  # Use first box for the signature field
        sig_page = int(box.get('page', 1)) - 1  # Convert to 0-indexed
        sig_x = float(box.get('x', 50))
        sig_y = float(box.get('y', 50))
        sig_width = float(box.get('width', 200))
        sig_height = float(box.get('height', 70))
        visible = True
    else:
        visible = request.form.get('visible', 'true') == 'true'
        sig_page = int(request.form.get('page', 1)) - 1
        sig_x = float(request.form.get('x', 50))
        sig_y = float(request.form.get('y', 50))
        sig_width = float(request.form.get('width', 200))
        sig_height = float(request.form.get('height', 70))

    if not pin:
        return jsonify({'error': 'PIN required'}), 400

    session = None
    try:
        from io import BytesIO
        from pyhanko.sign.pkcs11 import PKCS11Signer
        from pyhanko.sign.fields import SigFieldSpec, append_signature_field
        from pyhanko.sign import PdfSignatureMetadata
        from pyhanko.sign.signers.pdf_signer import PdfSigner
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        # Read PDF into BytesIO
        pdf_data = pdf_file.read()
        pdf_input = BytesIO(pdf_data)

        # Get custom PKCS11 path from form data
        custom_path = request.form.get('pkcs11_path')
        lib_path = get_pkcs11_lib_path(custom_path)

        # Load PKCS#11 library and find the right slot
        lib = pkcs11.lib(lib_path)
        slots = lib.get_slots(token_present=True)

        # Find slot by ID - python-pkcs11 uses slot array, not slot IDs directly
        target_slot = None
        for slot in slots:
            # The slot_id from frontend matches the PKCS#11 slot number
            if slot.slot_id == slot_id:
                target_slot = slot
                break

        if not target_slot:
            return jsonify({'error': f'Slot {slot_id} not found'}), 400

        # Open session with PIN
        token = target_slot.get_token()
        session = token.open(user_pin=pin)

        # Create PKCS#11 signer using pyHanko's built-in support
        # pyHanko handles ECDSA signatures correctly
        signer = PKCS11Signer(
            pkcs11_session=session,
            cert_label='Certificate ECC Advanced Signature',
            key_label='Private Key ECC Advanced Signature',
        )

        # Create signature metadata
        signature_meta = PdfSignatureMetadata(
            field_name='Signature1',
            reason=reason,
            location=location,
            contact_info=contact if contact else None,
        )

        # Prepare PDF writer (allow hybrid xref PDFs)
        from pyhanko.pdf_utils.reader import PdfFileReader
        pdf_reader = PdfFileReader(pdf_input, strict=False)
        pdf_writer = IncrementalPdfFileWriter.from_reader(pdf_reader)

        # Add signature field if visible
        if visible:
            # Get page dimensions to convert coordinates
            # Frontend uses top-left origin, PDF uses bottom-left
            page_obj = pdf_reader.root['/Pages']['/Kids'][sig_page]
            media_box = page_obj.get('/MediaBox', [0, 0, 612, 792])
            page_height = float(media_box[3]) - float(media_box[1])

            # Convert Y coordinate from top-left to bottom-left origin
            pdf_y = page_height - sig_y - sig_height

            sig_field_spec = SigFieldSpec(
                sig_field_name='Signature1',
                on_page=sig_page,
                box=(sig_x, pdf_y, sig_x + sig_width, pdf_y + sig_height),
            )
            append_signature_field(pdf_writer, sig_field_spec)

        # Create stamp background graphic (seal-like circle pattern)
        # Using PDF drawing commands for a circular seal
        seal_graphic = RawContent(
            box=None,  # Will be set by the stamp
            data=b'''
            q
            0.2 0.4 0.8 RG  % Blue stroke color
            0.9 0.95 1 rg  % Light blue fill
            2 w  % Line width
            50 35 40 30 re S  % Outer rectangle
            0.2 0.4 0.8 rg  % Blue fill for inner elements
            % Draw decorative lines
            15 60 m 135 60 l S  % Top line
            15 10 m 135 10 l S  % Bottom line
            Q
            '''
        )

        # Create stamp style with larger text and stamp-like appearance
        text_style = TextBoxStyle(
            font_size=28,  # Large font to fill the box
        )
        stamp_style = TextStampStyle(
            stamp_text='DIGITALLY SIGNED\n%(signer)s\n%(ts)s',
            text_box_style=text_style,
            border_width=3,
            border_color=(0.2, 0.4, 0.8),  # Blue border
            background=seal_graphic,
            background_opacity=0.15,  # Subtle background
        )

        # Create PdfSigner with stamp style
        pdf_signer = PdfSigner(
            signature_meta=signature_meta,
            signer=signer,
            stamp_style=stamp_style,
        )

        # Sign the PDF
        pdf_output = BytesIO()
        pdf_signer.sign_pdf(
            pdf_writer,
            output=pdf_output,
        )

        output_data = pdf_output.getvalue()

        # Close the PKCS#11 session
        if session:
            session.close()
            session = None

        # Save to temp file and return
        output_filename = f"signed_{secure_filename(pdf_file.filename)}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        with open(output_path, 'wb') as f:
            f.write(output_data)

        # Return as base64 for download
        return jsonify({
            'success': True,
            'filename': output_filename,
            'data': base64.b64encode(output_data).decode('ascii'),
            'size': len(output_data)
        })

    except pkcs11.PKCS11Error as e:
        error_msg = str(e)
        error_type = type(e).__name__
        if 'PIN' in error_msg.upper():
            return jsonify({'error': 'Incorrect PIN or PIN locked'}), 401
        return jsonify({'error': f'Smart card error ({error_type}): {error_msg}'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else error_type
        return jsonify({'error': f'{error_type}: {error_msg}'}), 500
    finally:
        # Always close the session
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/save-files', methods=['POST'])
def api_save_files():
    """Save signed files to Downloads folder and open in Finder"""
    import subprocess
    import zipfile
    from io import BytesIO

    data = request.json
    if not data or 'files' not in data:
        return jsonify({'error': 'No files provided'}), 400

    files_data = data['files']
    downloads_folder = os.path.expanduser('~/Downloads')

    try:
        saved_files = []

        if len(files_data) == 1:
            # Single file - save directly
            file_info = files_data[0]
            file_path = os.path.join(downloads_folder, file_info['name'])
            # Handle duplicate filenames
            base, ext = os.path.splitext(file_path)
            counter = 1
            while os.path.exists(file_path):
                file_path = f"{base}_{counter}{ext}"
                counter += 1

            file_bytes = base64.b64decode(file_info['data'])
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            saved_files.append(file_path)

            # Open Finder and select the file
            subprocess.run(['open', '-R', file_path], check=False)

        else:
            # Multiple files - create ZIP
            zip_path = os.path.join(downloads_folder, 'signed_documents.zip')
            # Handle duplicate filenames
            base, ext = os.path.splitext(zip_path)
            counter = 1
            while os.path.exists(zip_path):
                zip_path = f"{base}_{counter}{ext}"
                counter += 1

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_info in files_data:
                    file_bytes = base64.b64decode(file_info['data'])
                    zf.writestr(file_info['name'], file_bytes)

            saved_files.append(zip_path)

            # Open Finder and select the ZIP
            subprocess.run(['open', '-R', zip_path], check=False)

        return jsonify({
            'success': True,
            'saved_files': saved_files
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("CEI Web PDF Signer")
    print("="*60)
    print(f"\nPKCS#11 library: {get_pkcs11_lib_path()}")
    print(f"PyKCS11 available: {PKCS11_AVAILABLE}")
    print(f"pyHanko available: {PYHANKO_AVAILABLE}")
    print("\nOpen your browser and go to: http://localhost:5001")
    print("="*60 + "\n")

    # Use port 5001 to avoid conflict with macOS AirPlay Receiver on port 5000
    app.run(host='127.0.0.1', port=5001, debug=True)
