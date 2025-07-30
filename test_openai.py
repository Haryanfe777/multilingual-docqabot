import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Say hello!"}],
    max_tokens=2,
    temperature=0.2,
)
print(response.choices[0].message.content)