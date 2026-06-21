def log(msg):
    print("[LOG]", msg)


from engine.state import get_state

def get_snapshot():
    return get_state()
