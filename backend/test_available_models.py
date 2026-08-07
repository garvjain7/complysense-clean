import asyncio
from ai_service.config import get_ai_settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

candidates = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

async def main():
    settings = get_ai_settings()
    key = settings.gemini_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required to test Gemini models.")
    print(f"Testing API key (starts with {key[:6]}...)\n")
    for m in candidates:
        try:
            client = ChatGoogleGenerativeAI(model=m, google_api_key=key)
            resp = await client.ainvoke([HumanMessage(content="Reply OK")])
            print(f"[SUCCESS] model '{m}': {resp.content}")
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f"[QUOTA 429] model '{m}'")
            elif "404" in err_str:
                print(f"[NOT FOUND 404] model '{m}'")
            else:
                print(f"[ERROR] model '{m}': {err_str[:100]}")

if __name__ == "__main__":
    asyncio.run(main())
