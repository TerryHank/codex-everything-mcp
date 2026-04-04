from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path
from typing import Any

from ctypes import wintypes


EVERYTHING_OK = 0
EVERYTHING_ERROR_MEMORY = 1
EVERYTHING_ERROR_IPC = 2
EVERYTHING_ERROR_REGISTERCLASSEX = 3
EVERYTHING_ERROR_CREATEWINDOW = 4
EVERYTHING_ERROR_CREATETHREAD = 5
EVERYTHING_ERROR_INVALIDINDEX = 6
EVERYTHING_ERROR_INVALIDCALL = 7
EVERYTHING_ERROR_INVALIDREQUEST = 8
EVERYTHING_ERROR_INVALIDPARAMETER = 9

EVERYTHING_SORT_NAME_ASCENDING = 1
EVERYTHING_SORT_NAME_DESCENDING = 2
EVERYTHING_SORT_PATH_ASCENDING = 3
EVERYTHING_SORT_PATH_DESCENDING = 4
EVERYTHING_SORT_SIZE_ASCENDING = 5
EVERYTHING_SORT_SIZE_DESCENDING = 6
EVERYTHING_SORT_DATE_MODIFIED_ASCENDING = 13
EVERYTHING_SORT_DATE_MODIFIED_DESCENDING = 14
EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING = 22
EVERYTHING_SORT_DATE_ACCESSED_DESCENDING = 24
EVERYTHING_SORT_DATE_RUN_DESCENDING = 26

EVERYTHING_REQUEST_FILE_NAME = 0x00000001
EVERYTHING_REQUEST_PATH = 0x00000002
EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME = 0x00000004

TARGET_MACHINE_LABELS = {
    1: "x86",
    2: "x64",
    3: "arm",
}

SORT_VALUES = {
    "name_ascending": EVERYTHING_SORT_NAME_ASCENDING,
    "name_descending": EVERYTHING_SORT_NAME_DESCENDING,
    "path_ascending": EVERYTHING_SORT_PATH_ASCENDING,
    "path_descending": EVERYTHING_SORT_PATH_DESCENDING,
    "size_ascending": EVERYTHING_SORT_SIZE_ASCENDING,
    "size_descending": EVERYTHING_SORT_SIZE_DESCENDING,
    "date_modified_ascending": EVERYTHING_SORT_DATE_MODIFIED_ASCENDING,
    "date_modified_descending": EVERYTHING_SORT_DATE_MODIFIED_DESCENDING,
    "recently_changed_descending": EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING,
    "date_accessed_descending": EVERYTHING_SORT_DATE_ACCESSED_DESCENDING,
    "date_run_descending": EVERYTHING_SORT_DATE_RUN_DESCENDING,
}

ERROR_MESSAGES = {
    EVERYTHING_OK: "Everything query completed successfully.",
    EVERYTHING_ERROR_MEMORY: "Everything ran out of memory while processing the query.",
    EVERYTHING_ERROR_IPC: "Everything search client is not running.",
    EVERYTHING_ERROR_REGISTERCLASSEX: "Everything could not register its window class.",
    EVERYTHING_ERROR_CREATEWINDOW: "Everything could not create its reply window.",
    EVERYTHING_ERROR_CREATETHREAD: "Everything could not create its reply thread.",
    EVERYTHING_ERROR_INVALIDINDEX: "Everything reported an invalid result index.",
    EVERYTHING_ERROR_INVALIDCALL: "Everything reported an invalid call sequence.",
    EVERYTHING_ERROR_INVALIDREQUEST: "Everything reported invalid request data.",
    EVERYTHING_ERROR_INVALIDPARAMETER: "Everything reported an invalid parameter.",
}


class EverythingSDKError(RuntimeError):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"{message} (error_code={code})")
        self.code = code
        self.message = message


class EverythingClient:
    def __init__(self, dll_path: str | Path | None = None, library: Any | None = None) -> None:
        self.dll_path = str(Path(dll_path).resolve()) if dll_path else str(_default_dll_path().resolve())
        self._library = library if library is not None else self._load_library(self.dll_path)
        _configure_signatures(self._library)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
        match_path: bool = False,
        match_case: bool = False,
        whole_word: bool = False,
        regex: bool = False,
        sort: str = "name_ascending",
        kind: str = "all",
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if offset < 0:
            raise ValueError("offset must be 0 or greater")
        if sort not in SORT_VALUES:
            raise ValueError(f"unsupported sort: {sort}")
        if kind not in {"all", "file", "folder"}:
            raise ValueError(f"unsupported kind: {kind}")

        if kind == "all":
            return self._query_once(
                query=query,
                limit=limit,
                offset=offset,
                match_path=match_path,
                match_case=match_case,
                whole_word=whole_word,
                regex=regex,
                sort=sort,
            )

        desired_count = offset + limit
        batch_offset = 0
        batch_size = max(desired_count, 50)
        filtered: list[dict[str, Any]] = []
        total_results = 0

        while len(filtered) < desired_count:
            batch = self._query_once(
                query=query,
                limit=batch_size,
                offset=batch_offset,
                match_path=match_path,
                match_case=match_case,
                whole_word=whole_word,
                regex=regex,
                sort=sort,
            )
            total_results = batch["total_results"]
            batch_results = batch["results"]
            filtered.extend(item for item in batch_results if _matches_kind(item, kind))
            if len(batch_results) < batch_size:
                break
            batch_offset += batch_size

        window = filtered[offset:offset + limit]
        return {
            "query": query,
            "offset": offset,
            "limit": limit,
            "sort": sort,
            "kind": kind,
            "total_results": total_results,
            "returned": len(window),
            "results": window,
        }

    def health(self) -> dict[str, Any]:
        return {
            "dll_path": self.dll_path,
            "version": ".".join(
                str(part)
                for part in (
                    self._library.Everything_GetMajorVersion(),
                    self._library.Everything_GetMinorVersion(),
                    self._library.Everything_GetRevision(),
                    self._library.Everything_GetBuildNumber(),
                )
            ),
            "db_loaded": bool(self._library.Everything_IsDBLoaded()),
            "target_machine": TARGET_MACHINE_LABELS.get(
                self._library.Everything_GetTargetMachine(),
                "unknown",
            ),
        }

    def _query_once(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
        match_path: bool,
        match_case: bool,
        whole_word: bool,
        regex: bool,
        sort: str,
    ) -> dict[str, Any]:
        self._library.Everything_Reset()
        self._library.Everything_SetSearchW(query)
        self._library.Everything_SetMatchPath(bool(match_path))
        self._library.Everything_SetMatchCase(bool(match_case))
        self._library.Everything_SetMatchWholeWord(bool(whole_word))
        self._library.Everything_SetRegex(bool(regex))
        self._library.Everything_SetMax(int(limit))
        self._library.Everything_SetOffset(int(offset))
        self._library.Everything_SetSort(SORT_VALUES[sort])
        self._library.Everything_SetRequestFlags(
            EVERYTHING_REQUEST_FILE_NAME
            | EVERYTHING_REQUEST_PATH
            | EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME
        )

        ok = self._library.Everything_QueryW(True)
        if not ok:
            code = int(self._library.Everything_GetLastError())
            raise EverythingSDKError(code, ERROR_MESSAGES.get(code, "Everything query failed."))

        try:
            results = [self._read_result(index) for index in range(self._library.Everything_GetNumResults())]
            return {
                "query": query,
                "offset": offset,
                "limit": limit,
                "sort": sort,
                "kind": "all",
                "total_results": int(self._library.Everything_GetTotResults()),
                "returned": len(results),
                "results": results,
            }
        finally:
            self._library.Everything_Reset()

    def _read_result(self, index: int) -> dict[str, Any]:
        name = str(self._library.Everything_GetResultFileNameW(index))
        path = _read_full_path(self._library, index)
        is_file = bool(self._library.Everything_IsFileResult(index))
        is_folder = bool(self._library.Everything_IsFolderResult(index))
        return {
            "name": name,
            "path": path,
            "is_file": is_file,
            "is_folder": is_folder,
        }

    @staticmethod
    def _load_library(dll_path: str) -> Any:
        if sys.platform != "win32":
            raise RuntimeError("Everything MCP only supports Windows hosts.")
        return ctypes.WinDLL(dll_path)


def _read_full_path(library: Any, index: int) -> str:
    required = int(library.Everything_GetResultFullPathNameW(index, None, 0))
    if required <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(required + 1)
    library.Everything_GetResultFullPathNameW(index, buffer, len(buffer))
    return str(buffer.value)


def _matches_kind(item: dict[str, Any], kind: str) -> bool:
    if kind == "file":
        return bool(item["is_file"])
    if kind == "folder":
        return bool(item["is_folder"])
    return True


def _default_dll_path() -> Path:
    env_path = Path(os.environ["EVERYTHING_SDK_DLL"]).expanduser() if "EVERYTHING_SDK_DLL" in os.environ else None
    if env_path is not None:
        return env_path

    project_root = Path(__file__).resolve().parents[2]
    sdk_root = Path(os.environ["EVERYTHING_SDK_ROOT"]).expanduser() if "EVERYTHING_SDK_ROOT" in os.environ else project_root.parent
    arch_map = {
        "ARM64": "EverythingARM64.dll",
        "ARM": "EverythingARM.dll",
        "64bit": "Everything64.dll",
        "32bit": "Everything32.dll",
    }
    machine = platform.machine().upper()
    architecture = platform.architecture()[0]

    if "ARM64" in machine:
        dll_name = arch_map["ARM64"]
    elif "ARM" in machine:
        dll_name = arch_map["ARM"]
    else:
        dll_name = arch_map.get(architecture, "Everything64.dll")
    return Path(sdk_root) / "dll" / dll_name


def _configure_signatures(library: Any) -> None:
    _set_signature(library, "Everything_SetSearchW", None, [wintypes.LPCWSTR])
    _set_signature(library, "Everything_SetMatchPath", None, [wintypes.BOOL])
    _set_signature(library, "Everything_SetMatchCase", None, [wintypes.BOOL])
    _set_signature(library, "Everything_SetMatchWholeWord", None, [wintypes.BOOL])
    _set_signature(library, "Everything_SetRegex", None, [wintypes.BOOL])
    _set_signature(library, "Everything_SetMax", None, [wintypes.DWORD])
    _set_signature(library, "Everything_SetOffset", None, [wintypes.DWORD])
    _set_signature(library, "Everything_SetSort", None, [wintypes.DWORD])
    _set_signature(library, "Everything_SetRequestFlags", None, [wintypes.DWORD])
    _set_signature(library, "Everything_QueryW", wintypes.BOOL, [wintypes.BOOL])
    _set_signature(library, "Everything_GetLastError", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetNumResults", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetTotResults", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetResultFileNameW", wintypes.LPCWSTR, [wintypes.DWORD])
    _set_signature(
        library,
        "Everything_GetResultFullPathNameW",
        wintypes.DWORD,
        [wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD],
    )
    _set_signature(library, "Everything_IsFileResult", wintypes.BOOL, [wintypes.DWORD])
    _set_signature(library, "Everything_IsFolderResult", wintypes.BOOL, [wintypes.DWORD])
    _set_signature(library, "Everything_Reset", None, [])
    _set_signature(library, "Everything_GetMajorVersion", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetMinorVersion", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetRevision", wintypes.DWORD, [])
    _set_signature(library, "Everything_GetBuildNumber", wintypes.DWORD, [])
    _set_signature(library, "Everything_IsDBLoaded", wintypes.BOOL, [])
    _set_signature(library, "Everything_GetTargetMachine", wintypes.DWORD, [])


def _set_signature(library: Any, func_name: str, restype: Any, argtypes: list[Any]) -> None:
    func = getattr(library, func_name, None)
    if func is None:
        return
    try:
        func.restype = restype
        func.argtypes = argtypes
    except AttributeError:
        return
