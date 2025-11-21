import signal
import traceback

from app.graph import builder

state = {
    "messages": [{"type": "human", "content": "Oi"}],
    "user_id": "me",
    "route": "",
    "final_context": [],
    "final_response": "",
}


def handler(signum, frame):
    raise TimeoutError("invoke timed out (8s)")


if __name__ == "__main__":
    print("Invoking app_graph.invoke(state) with 8s timeout...")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(8)
    try:
        res = builder.app_graph.invoke(state)
        print("Result:", res)
    except Exception:
        traceback.print_exc()
    finally:
        signal.alarm(0)
