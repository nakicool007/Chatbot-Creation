from collections import Counter
from math import log, sqrt
import unittest

import aiapp


def build_test_knowledge_base(texts: list[tuple[str, int, str]]) -> dict[str, object]:
    chunks: list[dict[str, object]] = []
    for source, page, text in texts:
        counts = Counter(aiapp.tokenize(text))
        chunks.append(
            {
                "source": source,
                "page": page,
                "chunk": 1,
                "text": text,
                "counts": dict(counts),
            }
        )

    document_frequency: Counter[str] = Counter()
    for chunk in chunks:
        document_frequency.update(chunk["counts"].keys())

    idf = {
        term: log((1 + len(chunks)) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }

    for chunk in chunks:
        weights: dict[str, float] = {}
        norm = 0.0
        for term, frequency in chunk["counts"].items():
            weight = (1 + log(frequency)) * idf[term]
            weights[term] = weight
            norm += weight * weight
        chunk["weights"] = weights
        chunk["norm"] = sqrt(norm) or 1.0
        del chunk["counts"]

    return {"chunks": chunks, "idf": idf, "errors": []}


class RetrievalTests(unittest.TestCase):
    def test_retrieve_chunks_returns_best_match_first(self) -> None:
        knowledge_base = build_test_knowledge_base(
            [
                (
                    "resource.pdf",
                    3,
                    "Resource managers allocate capacity and review resource demand.",
                ),
                (
                    "work.pdf",
                    7,
                    "Work managers create project tasks and update task progress.",
                ),
            ]
        )

        matches = aiapp.retrieve_chunks(
            knowledge_base,
            "How do resource managers allocate capacity?",
            top_k=2,
            min_score=0.01,
        )

        self.assertGreaterEqual(len(matches), 1)
        self.assertEqual(matches[0]["source"], "resource.pdf")

    def test_retrieve_chunks_returns_empty_for_unmatched_query(self) -> None:
        knowledge_base = build_test_knowledge_base(
            [
                (
                    "resource.pdf",
                    3,
                    "Resource managers allocate capacity and review resource demand.",
                )
            ]
        )

        matches = aiapp.retrieve_chunks(
            knowledge_base,
            "cafeteria lunch menu",
            top_k=2,
            min_score=0.01,
        )

        self.assertEqual(matches, [])


class PromptTests(unittest.TestCase):
    def test_build_model_messages_includes_system_prompt_and_context(self) -> None:
        messages = aiapp.build_model_messages(
            history=[{"role": "user", "content": "previous question"}],
            user_prompt="How do I submit work?",
            context="[Source 1: work.pdf, p. 2]\nSubmit work from the work page.",
            use_playbooks=True,
            history_limit=4,
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("only the supplied playbook context", messages[0]["content"])
        self.assertIn("Playbook context", messages[-1]["content"])
        self.assertIn("work.pdf", messages[-1]["content"])

    def test_build_model_messages_limits_history(self) -> None:
        history = [
            {"role": "user", "content": f"question {index}"}
            for index in range(5)
        ]

        messages = aiapp.build_model_messages(
            history=history,
            user_prompt="new question",
            context="context",
            use_playbooks=False,
            history_limit=2,
        )

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["content"], "question 3")


class ModelDiscoveryTests(unittest.TestCase):
    def test_select_model_options_maps_latest_aliases(self) -> None:
        selected = aiapp.select_model_options(
            available_models=["llama3.2:latest", "qwen3:8b"],
            allowed_models=["llama3.2", "deepseek-r1:7b", "qwen3:8b"],
        )

        self.assertEqual(selected, ["llama3.2:latest", "qwen3:8b"])

    def test_extract_model_names_accepts_dict_responses(self) -> None:
        model_names = aiapp.extract_model_names(
            {"models": [{"model": "llama3.2:latest"}, {"name": "qwen3:8b"}]}
        )

        self.assertEqual(model_names, ["llama3.2:latest", "qwen3:8b"])


if __name__ == "__main__":
    unittest.main()
