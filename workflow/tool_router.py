from dataclasses import dataclass

from models.search_type import SearchType



@dataclass
class RoutedTools:
    """
    Result returned by ToolRouter.

    Contains tools allowed for this
    research sub-question.
    """

    tools: list[str]



class ToolRouter:
    """
    Decide which tools should be used
    according to Planner output.
    """


    def route(
        self,
        search_type: SearchType,
    ) -> RoutedTools:


        if isinstance(
            search_type,
            str,
        ):
            try:
                search_type = (
                    SearchType(
                        search_type
                    )
                )

            except ValueError:
                raise ValueError(
                    f"Unsupported search type: "
                    f"{search_type}"
                )


        if (
            search_type
            == SearchType.PAPER_SEARCH
        ):

            return RoutedTools(
                tools=[
                    "paper_search"
                ]
            )


        if (
            search_type
            == SearchType.WEB_SEARCH
        ):

            return RoutedTools(
                tools=[
                    "web_search"
                ]
            )


        if (
            search_type
            == SearchType.HYBRID
        ):

            return RoutedTools(
                tools=[
                    "paper_search",
                    "web_search",
                ]
            )


        raise ValueError(
            f"Unsupported search type: "
            f"{search_type}"
        )