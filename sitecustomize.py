"""Windows asyncio compatibility for HYDRORESQ.

Use the Selector event loop on Windows to avoid benign Proactor
connection-reset tracebacks from short-lived localhost health checks.
"""
import asyncio

if __import__("sys").platform == "win32":
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is not None:
        asyncio.set_event_loop_policy(policy())
