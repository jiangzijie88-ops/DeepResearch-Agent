from memory.memory_item import (
    MemoryItem,
)



class MemoryStore:


    def __init__(self):

        self.items = []



    def add(
        self,
        item: MemoryItem,
    ):

        self.items.append(
            item
        )



    def search(
        self,
        keyword: str,
    ):

        results = []


        for item in self.items:

            if (
                keyword.lower()
                in
                item.question.lower()
            ):

                results.append(
                    item
                )


        return results



    def get_all(self):

        return self.items



    def __len__(self):

        return len(
            self.items
        )