from models.evidence import Evidence


class EvidenceStore:

    def __init__(self):

        self.evidence_list: list[Evidence] = []

        self._seen_keys: set[str] = set()


    def _get_key(
        self,
        evidence: Evidence
    ) -> str:

        if evidence.doi:

            return evidence.doi.lower().strip()

        return evidence.title.lower().strip()


    def add(
        self,
        evidence: Evidence
    ) -> bool:

        key = self._get_key(evidence)

        if key in self._seen_keys:

            return False

        self._seen_keys.add(key)

        self.evidence_list.append(
            evidence
        )

        return True


    def add_many(
        self,
        evidence_items: list[Evidence]
    ) -> int:

        added_count = 0

        for evidence in evidence_items:

            if self.add(evidence):

                added_count += 1

        return added_count


    def get_all(
        self
    ) -> list[Evidence]:

        return self.evidence_list


    def count(
        self
    ) -> int:

        return len(
            self.evidence_list
        )