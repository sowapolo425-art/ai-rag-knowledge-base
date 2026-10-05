import re

from openai import OpenAI

from .config import Settings


def _best_excerpt(question: str, text: str) -> str:
    sentences = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s*", text) if item.strip()]
    if not sentences:
        return text[:300]
    terms = set(re.findall(r"[\w]+", question.lower()))
    terms.update(question[i:i + 2] for i in range(max(0, len(question) - 1)))
    return max(sentences, key=lambda item: sum(term in item.lower() for term in terms))[:400]


def answer(question: str, hits: list[dict], settings: Settings, history: list | None = None) -> str:
    if not hits:
        return "我没有在已上传的文档中找到足够相关的依据。请换个问法或上传相关资料。"
    if settings.api_key and settings.chat_model:
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        context = "\n\n".join(f"[{i}] {hit['filename']} · {hit['locator']}\n{hit['text']}" for i, hit in enumerate(hits, 1))
        recent = "\n".join(f"{item.role}: {item.content}" for item in (history or []))
        completion = client.chat.completions.create(
            model=settings.chat_model,
            temperature=0,
            messages=[
                {"role": "system", "content": "你是企业知识库问答助手。只能根据本轮提供的文档片段回答。历史对话仅用于理解指代，不能作为事实依据。每项具体事实后标注对应编号，如 [1]。若文档没有答案，明确说不知道，不要补充外部知识。"},
                {"role": "user", "content": f"近期对话：\n{recent}\n\n本轮问题：{question}\n\n本轮文档片段：\n{context}"},
            ],
        )
        return (completion.choices[0].message.content or "模型未返回答案。").strip()
    return "根据文档，最相关的内容是：\n\n" + "\n\n".join(f"[{i}] {_best_excerpt(question, hit['text'])}" for i, hit in enumerate(hits[:3], 1))
