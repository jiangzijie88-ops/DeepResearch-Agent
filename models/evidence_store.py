import re

from models.evidence import Evidence


class EvidenceStore:

    def __init__(self):
        self._items: list[Evidence] = []
        self._next_id = 1


    # ========================================================
    # Public API
    # ========================================================

    def add_many(
        self,
        evidence_list: list[Evidence],
    ) -> int:
        added_count = 0
        # Reserve checkpoint IDs before assigning IDs to legacy entries.
        reserved = {e.evidence_id for e in evidence_list if e.evidence_id}
        used = {e.evidence_id for e in self._items}

        for evidence in evidence_list:

            existing = self._find_duplicate(
                evidence
            )

            if existing is None:
                if evidence.evidence_id is None:
                    while f"E{self._next_id}" in reserved | used:
                        self._next_id += 1
                    evidence.evidence_id = f"E{self._next_id}"
                elif evidence.evidence_id in used:
                    raise ValueError(f"Conflicting Evidence ID: {evidence.evidence_id}")
                used.add(evidence.evidence_id)
                self._next_id = max(self._next_id, int(evidence.evidence_id[1:]) + 1)

                self._items.append(
                    evidence
                )

                added_count += 1

            else:

                self._merge_evidence(
                    existing,
                    evidence,
                )

        return added_count


    def get_all(
        self,
    ) -> list[Evidence]:
        return list(
            self._items
        )


    def count(
        self,
    ) -> int:
        return len(
            self._items
        )


    def __len__(
        self,
    ) -> int:
        return self.count()


    # ========================================================
    # Duplicate Detection
    # ========================================================

    def _find_duplicate(
        self,
        incoming: Evidence,
    ) -> Evidence | None:

        for existing in self._items:

            if self._same_evidence(
                existing,
                incoming,
            ):
                return existing

        return None


    def _same_evidence(
        self,
        first: Evidence,
        second: Evidence,
    ) -> bool:

        first_doi = self._normalize_doi(
            first.doi
        )

        second_doi = self._normalize_doi(
            second.doi
        )


        # DOI 是学术论文最强 identity。
        if first_doi and second_doi:

            return (
                first_doi
                == second_doi
            )


        first_url = self._normalize_url(
            first.url
        )

        second_url = self._normalize_url(
            second.url
        )


        # 没有共同 DOI 时，再比较 URL。
        if first_url and second_url:

            if first_url == second_url:
                return True


        first_title = self._normalize_title(
            first.title
        )

        second_title = self._normalize_title(
            second.title
        )


        if (
            not first_title
            or not second_title
        ):
            return False


        if first_title != second_title:
            return False


        # 标题相同时：
        # 如果两个 year 都存在，则要求 year 也相同。
        if (
            first.year is not None
            and second.year is not None
        ):

            return (
                first.year
                == second.year
            )


        # 某一侧缺少年份时，
        # 标题完全规范化一致即可认为是同一 Evidence。
        return True


    # ========================================================
    # Normalization
    # ========================================================

    @staticmethod
    def _normalize_doi(
        doi: str | None,
    ) -> str | None:

        if not doi:
            return None

        normalized = (
            doi
            .strip()
            .lower()
        )

        prefixes = (
            "https://doi.org/",
            "http://doi.org/",
            "http://dx.doi.org/",
            "https://dx.doi.org/",
            "doi:",
        )

        for prefix in prefixes:

            if normalized.startswith(
                prefix
            ):

                normalized = (
                    normalized[
                        len(prefix):
                    ]
                )

                break

        normalized = (
            normalized
            .strip()
            .rstrip("/")
        )

        return (
            normalized
            or None
        )


    @staticmethod
    def _normalize_url(
        url: str | None,
    ) -> str | None:

        if not url:
            return None

        normalized = (
            url
            .strip()
            .lower()
            .rstrip("/")
        )

        return (
            normalized
            or None
        )


    @staticmethod
    def _normalize_title(
        title: str | None,
    ) -> str:

        if not title:
            return ""

        normalized = (
            title
            .strip()
            .lower()
        )

        normalized = re.sub(
            r"[^\w\s]",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized.strip()


    # ========================================================
    # Merge
    # ========================================================

    @staticmethod
    def _merge_evidence(
        existing: Evidence,
        incoming: Evidence,
    ) -> None:

        # ----------------------------------------------------
        # Authors
        # ----------------------------------------------------

        merged_authors = list(
            existing.authors
        )

        for author in incoming.authors:

            if (
                author
                not in merged_authors
            ):

                merged_authors.append(
                    author
                )

        existing.authors = (
            merged_authors
        )


        # ----------------------------------------------------
        # Fill missing scalar metadata
        # ----------------------------------------------------

        fields_to_fill = (
            "venue",
            "published_at",
            "doi",
            "url",
            "summary",
            "query",
            "retrieved_at",
            "confidence",
        )

        for field_name in fields_to_fill:

            existing_value = getattr(
                existing,
                field_name,
            )

            incoming_value = getattr(
                incoming,
                field_name,
            )

            if (
                existing_value is None
                or existing_value == ""
            ):

                if (
                    incoming_value
                    is not None
                    and incoming_value != ""
                ):

                    setattr(
                        existing,
                        field_name,
                        incoming_value,
                    )


        # ----------------------------------------------------
        # Year
        # ----------------------------------------------------

        if (
            existing.year is None
            and incoming.year is not None
        ):
            existing.year = (
                incoming.year
            )


        # ----------------------------------------------------
        # Citation Count
        # ----------------------------------------------------

        if incoming.citations is not None:

            if (
                existing.citations is None
                or incoming.citations
                > existing.citations
            ):

                existing.citations = (
                    incoming.citations
                )


        # ----------------------------------------------------
        # Verified
        # ----------------------------------------------------

        existing.verified = (
            existing.verified
            or incoming.verified
        )


        # ----------------------------------------------------
        # Source
        # ----------------------------------------------------

        existing_sources = [
            item.strip()
            for item in (
                existing.source
                or ""
            ).split("|")
            if item.strip()
        ]

        incoming_sources = [
            item.strip()
            for item in (
                incoming.source
                or ""
            ).split("|")
            if item.strip()
        ]

        for source in incoming_sources:

            if source not in existing_sources:

                existing_sources.append(
                    source
                )

        if existing_sources:

            existing.source = (
                " | ".join(
                    existing_sources
                )
            )
