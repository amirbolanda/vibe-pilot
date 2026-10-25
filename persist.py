"""Optional cloud persistence (used only when deployed). On your laptop nothing happens: without HF_TOKEN / HF_DATA_REPO every function is a no-op.
A private Hugging Face *dataset* repo holds the workbook and feedback.db, so they never sit in the public code repo and survive restarts."""
import os, threading

REPO = os.environ.get('HF_DATA_REPO')          # e.g. "yourname/vibe-private-data"  (a PRIVATE dataset repo)
TOKEN = os.environ.get('HF_TOKEN')             # a token with write access to that repo
ON = bool(REPO and TOKEN)
_timer = None; _lock = threading.Lock()

def fetch(filename, dest=None):
    """download `filename` from the private repo into the working folder; True on success"""
    if not ON: return False
    try:
        from huggingface_hub import hf_hub_download
        import shutil
        p = hf_hub_download(repo_id=REPO, filename=filename, repo_type='dataset', token=TOKEN, force_download=True)
        shutil.copy(p, dest or filename); return True
    except Exception as e:
        print('[persist] fetch failed:', filename, type(e).__name__); return False

def _push(path):
    try:
        from huggingface_hub import HfApi
        HfApi(token=TOKEN).upload_file(path_or_fileobj=path, path_in_repo=os.path.basename(path), repo_id=REPO, repo_type='dataset')
    except Exception as e:
        print('[persist] push failed:', type(e).__name__)

def push_later(path='feedback.db', delay=8):
    """debounced upload: many quick writes -> one upload `delay` seconds after the last one"""
    global _timer
    if not ON: return
    with _lock:
        if _timer: _timer.cancel()
        _timer = threading.Timer(delay, _push, args=(path,)); _timer.daemon = True; _timer.start()
