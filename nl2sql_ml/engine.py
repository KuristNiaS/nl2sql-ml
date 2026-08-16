from __future__ import annotations

from pathlib import Path
from typing import Any

from .compiler import SQLCompiler
from .model import ModelBundle
from .schema import load_catalog, load_dictionary, load_semantic_layer, project_root
from .semantic import SemanticParser


class NL2SQLEngine:
    def __init__(
        self,
        catalog_path: str | Path | None = None,
        dictionary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        semantic_layer_path: str | Path | None = None,
    ):
        self.catalog = load_catalog(catalog_path)
        self.dictionary = load_dictionary(dictionary_path)
        self.semantic_layer = load_semantic_layer(semantic_layer_path)
        resolved_model = Path(model_path) if model_path else project_root() / "artifacts" / "model.joblib"
        if not resolved_model.exists():
            raise FileNotFoundError("模型不存在，请先执行 python -m nl2sql_ml build")
        self.models = ModelBundle(resolved_model, self.catalog, self.semantic_layer)
        self.parser = SemanticParser(self.catalog, self.dictionary, self.models, self.semantic_layer)
        self.compiler = SQLCompiler(self.catalog, self.semantic_layer)

    def translate(self, question: str) -> dict[str, Any]:
        plan = self.parser.parse(question)
        sql, params = self.compiler.compile(plan)
        return {"question": question, "sql": sql, "params": params, "plan": plan}
