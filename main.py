#!/usr/bin/env python3
"""
CEI PDF Signer - Desktop Application
Wraps the Flask web app in a native macOS window using PyWebView
"""

import sys
import os
import threading
import socket
import time

# Ensure we can find our modules when running as a bundled app
if getattr(sys, 'frozen', False):
    # Running as bundled app
    bundle_dir = os.path.dirname(sys.executable)
    # For py2app, resources are in ../Resources
    resources_dir = os.path.join(os.path.dirname(bundle_dir), 'Resources')
    if os.path.exists(resources_dir):
        os.chdir(resources_dir)
        sys.path.insert(0, resources_dir)

import webview
from app import app


def find_free_port():
    """Find a free port to run the server on"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_server(port):
    """Start the Flask server in a background thread"""
    # Disable Flask's reloader and debug mode for production
    # threaded=False so signal.alarm timeout works for PKCS11
    app.run(
        host='127.0.0.1',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=False
    )


def wait_for_server(port, timeout=10):
    """Wait for the server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', port))
                return True
        except ConnectionRefusedError:
            time.sleep(0.1)
    return False


def on_loaded():
    """Called when the window is loaded - bring to front"""
    time.sleep(0.3)  # Small delay to ensure window is ready
    # On macOS, use AppleScript to bring app to front
    if sys.platform == 'darwin':
        import subprocess
        subprocess.run([
            'osascript', '-e',
            'tell application "System Events" to set frontmost of the first process whose unix id is {} to true'.format(os.getpid())
        ], check=False)


def main():
    # Find a free port
    port = find_free_port()

    # Start Flask server in background thread
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    if not wait_for_server(port):
        print("Error: Server failed to start")
        sys.exit(1)

    # Create the native window
    window = webview.create_window(
        title='CEI PDF Signer',
        url=f'http://127.0.0.1:{port}',
        width=1280,
        height=800,
        min_size=(1000, 600),
        resizable=True,
        confirm_close=True,
        text_select=True,
        on_top=True,  # Start on top
    )

    # Start the GUI with loaded callback
    def bring_to_front():
        time.sleep(0.5)
        window.on_top = False  # Disable always-on-top after showing

    webview.start(
        func=bring_to_front,
        debug=False,
        private_mode=False,  # Allow cookies/storage
    )


if __name__ == '__main__':
    main()
