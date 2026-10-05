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
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url, timeout=90, max_retries=0)
        context = "\n".join(f"资料[{i}]：{hit['text'][:450]}" for i, hit in enumerate(hits, 1))
        recent_questions = "；".join(item.content for item in (history or []) if item.role == "user")
        previous = f"上轮问题（只用于理解这次提问）：{recent_questions}\n" if recent_questions else ""
        completion = client.chat.completions.create(
            model=settings.chat_model,
            temperature=0,
            max_tokens=200,
            messages=[
                {"role": "system", "content": "根据资料用完整句子回答。检查并写出所有适用条件、审批步骤和额外要求。资料没有答案就说不知道，不要猜测。"},
                {"role": "user", "content": f"{context}\n{previous}问题：{question} 请完整回答，并在答案后写对应的引用编号，例如 [1]。"},
            ],
        )
        result = (completion.choices[0].message.content or "模型未返回答案。").strip()
        if len(hits) == 1 and "[1]" not in result and "不知道" not in result and result != "模型未返回答案。":
            result += " [1]"
        return result
    return "根据文档，最相关的内容是：\n\n" + "\n\n".join(f"[{i}] {_best_excerpt(question, hit['text'])}" for i, hit in enumerate(hits[:3], 1))
