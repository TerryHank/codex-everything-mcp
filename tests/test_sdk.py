from __future__ import annotations

import unittest

from codex_everything_mcp.sdk import EVERYTHING_ERROR_IPC, EverythingClient, EverythingSDKError


class FakeEverythingLibrary:
    def __init__(self) -> None:
        self.search = None
        self.match_path = None
        self.match_case = None
        self.match_whole_word = None
        self.regex = None
        self.max_value = None
        self.offset_value = None
        self.sort_value = None
        self.request_flags = None
        self.last_error = 0
        self.query_success = True
        self.results = [
            {
                "path": r"C:\docs\report.txt",
                "name": "report.txt",
                "is_file": True,
                "is_folder": False,
            }
        ]

    def Everything_SetSearchW(self, value: str) -> None:
        self.search = value

    def Everything_SetMatchPath(self, value: bool) -> None:
        self.match_path = bool(value)

    def Everything_SetMatchCase(self, value: bool) -> None:
        self.match_case = bool(value)

    def Everything_SetMatchWholeWord(self, value: bool) -> None:
        self.match_whole_word = bool(value)

    def Everything_SetRegex(self, value: bool) -> None:
        self.regex = bool(value)

    def Everything_SetMax(self, value: int) -> None:
        self.max_value = value

    def Everything_SetOffset(self, value: int) -> None:
        self.offset_value = value

    def Everything_SetSort(self, value: int) -> None:
        self.sort_value = value

    def Everything_SetRequestFlags(self, value: int) -> None:
        self.request_flags = value

    def Everything_QueryW(self, wait: bool) -> bool:
        return self.query_success

    def Everything_GetLastError(self) -> int:
        return self.last_error

    def Everything_GetNumResults(self) -> int:
        return len(self.results)

    def Everything_GetTotResults(self) -> int:
        return len(self.results)

    def Everything_GetResultFullPathNameW(self, index: int, buffer, buffer_size: int) -> int:
        value = self.results[index]["path"]
        if buffer_size == 0:
            return len(value)
        buffer.value = value[: max(0, buffer_size - 1)]
        return len(value)

    def Everything_GetResultFileNameW(self, index: int) -> str:
        return self.results[index]["name"]

    def Everything_IsFileResult(self, index: int) -> bool:
        return self.results[index]["is_file"]

    def Everything_IsFolderResult(self, index: int) -> bool:
        return self.results[index]["is_folder"]

    def Everything_Reset(self) -> None:
        return None

    def Everything_CleanUp(self) -> None:
        return None

    def Everything_GetMajorVersion(self) -> int:
        return 1

    def Everything_GetMinorVersion(self) -> int:
        return 4

    def Everything_GetRevision(self) -> int:
        return 1

    def Everything_GetBuildNumber(self) -> int:
        return 1026

    def Everything_IsDBLoaded(self) -> bool:
        return True

    def Everything_GetTargetMachine(self) -> int:
        return 2


class EverythingClientTests(unittest.TestCase):
    def test_search_raises_helpful_error_when_everything_is_not_running(self) -> None:
        library = FakeEverythingLibrary()
        library.query_success = False
        library.last_error = EVERYTHING_ERROR_IPC

        client = EverythingClient(library=library, dll_path="fake.dll")

        with self.assertRaises(EverythingSDKError) as error:
            client.search("report")

        self.assertIn("Everything search client is not running", str(error.exception))

    def test_search_maps_query_options_and_returns_results(self) -> None:
        library = FakeEverythingLibrary()
        client = EverythingClient(library=library, dll_path="fake.dll")

        result = client.search(
            "report",
            limit=5,
            offset=2,
            match_path=True,
            match_case=True,
            whole_word=True,
            regex=True,
            sort="size_descending",
        )

        self.assertEqual("report", library.search)
        self.assertTrue(library.match_path)
        self.assertTrue(library.match_case)
        self.assertTrue(library.match_whole_word)
        self.assertTrue(library.regex)
        self.assertEqual(5, library.max_value)
        self.assertEqual(2, library.offset_value)
        self.assertEqual(6, library.sort_value)
        self.assertEqual(1, result["returned"])
        self.assertEqual(r"C:\docs\report.txt", result["results"][0]["path"])

    def test_search_reads_full_path_without_truncating_last_character(self) -> None:
        library = FakeEverythingLibrary()
        library.results = [
            {
                "path": r"F:\Download\Everything-SDK\codex_everything_mcp\.venv",
                "name": ".venv",
                "is_file": False,
                "is_folder": True,
            }
        ]
        client = EverythingClient(library=library, dll_path="fake.dll")

        result = client.search("Everything-SDK", limit=1, match_path=True)

        self.assertEqual(
            r"F:\Download\Everything-SDK\codex_everything_mcp\.venv",
            result["results"][0]["path"],
        )

    def test_health_reports_sdk_metadata(self) -> None:
        client = EverythingClient(library=FakeEverythingLibrary(), dll_path="fake.dll")

        result = client.health()

        self.assertEqual("1.4.1.1026", result["version"])
        self.assertTrue(result["db_loaded"])
        self.assertEqual("x64", result["target_machine"])


if __name__ == "__main__":
    unittest.main()
