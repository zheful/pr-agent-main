from openai import OpenAI
import os

c = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"]
)

res = c.chat.completions.create(
    model=os.environ["OPENAI_MODEL"],
    messages=[{"role":"user","content":"输出OK"}]
)
print(res.choices[0].message.content)


