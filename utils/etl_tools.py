
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
import pandas as pd
from bs4 import BeautifulSoup


class ETLTools:
    """Tools for extracting, saving, and inspecting data."""

    SUPPORTED_FORMATS = {"csv", "json", "parquet"}

    def __init__(self):
        # Assumes this file is in a subdirectory of the project root.
        self.project_root = Path(__file__).resolve().parent.parent

    def _resolve_output_folder(self, output_folder: str) -> Path:
        """Resolve output paths relative to the project root."""
        path = Path(output_folder)

        if not path.is_absolute():
            path = self.project_root / path

        return path.resolve()

    def _extract_json(self, data):
        """Convert common JSON API response structures to a DataFrame."""

        if isinstance(data, list):
            records = data

        elif isinstance(data, dict):
            # Common API response keys that contain records.
            records = None

            for key in ("results", "data", "items", "records"):
                if key in data:
                    records = data[key]
                    break

            if records is None:
                records = [data]

        else:
            raise ValueError("Unsupported JSON response structure.")

        if isinstance(records, list):
            return pd.json_normalize(records)

        if isinstance(records, dict):
            return pd.json_normalize([records])

        raise ValueError(
            "The API's results/data field must contain a list or object."
        )

    def _extract_html(self, html: str) -> pd.DataFrame:
        """Extract headings, paragraphs, and list items in document order."""

        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements.
        for tag in soup(
            ["script", "style", "noscript", "nav", "footer", "svg"]
        ):
            tag.decompose()

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )

        # Prefer the main article/content area when available.
        main = soup.find("article") or soup.find("main") or soup.body or soup

        records = []

        for element in main.find_all(
            ["h1", "h2", "h3", "h4", "p", "li"]
        ):
            text = element.get_text(" ", strip=True)

            if text:
                records.append({
                    "page_title": title,
                    "element_type": element.name,
                    "content": text
                })

        if not records:
            text = main.get_text(" ", strip=True)

            if text:
                records.append({
                    "page_title": title,
                    "element_type": "text",
                    "content": text
                })

        if not records:
            raise ValueError(
                "No readable content was found in the HTML response."
            )

        return pd.DataFrame(records)

    def _save_dataframe(
        self,
        df: pd.DataFrame,
        output_path: Path,
        format: str
    ) -> Path:
        """Save a DataFrame using the requested output format."""

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            df.to_csv(
                output_path,
                index=False,
                encoding="utf-8-sig"
            )

        elif format == "json":
            df.to_json(
                output_path,
                orient="records",
                indent=2,
                force_ascii=False
            )

        elif format == "parquet":
            df.to_parquet(output_path, index=False)

        return output_path

    def extract_load(
        self,
        url: str,
        output_folder: str,
        format: str = "csv"
    ) -> dict:
        """
        Fetch a JSON API or HTML webpage and save its extracted content.

        Args:
            url: HTTP or HTTPS URL.
            output_folder: Output directory or file path, relative to project root
                unless an absolute path is provided.
            format: csv, json, or parquet.

        Returns:
            A dictionary containing success status, record count,
            output path, or error details.
        """

        format = format.lower().strip().lstrip(".")

        if format not in self.SUPPORTED_FORMATS:
            return {
                "success": False,
                "error_type": "unsupported_format",
                "message": f"Unsupported format: {format}"
            }

        # Validate URL before sending a request.
        parsed_url = urlparse(url)

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
        ):
            return {
                "success": False,
                "error_type": "invalid_url",
                "message": "Provide a valid HTTP or HTTPS URL."
            }

        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30
            )
            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            # Extract data according to the response content type.
            if "json" in content_type:
                df = self._extract_json(response.json())

            elif "html" in content_type or (
                "text/plain" in content_type
                and "<html" in response.text[:2000].lower()
            ):
                df = self._extract_html(response.text)

            else:
                return {
                    "success": False,
                    "error_type": "unsupported_content_type",
                    "message": (
                        "Cannot process response content type: "
                        f"{content_type or 'unknown'}"
                    )
                }

            if df.empty:
                return {
                    "success": False,
                    "error_type": "empty_data",
                    "message": "The response contained no extractable records."
                }

            # Determine whether output_folder is a file path or directory path
            raw_path = Path(output_folder)
            if not raw_path.is_absolute():
                resolved = (self.project_root / raw_path).resolve()
            else:
                resolved = raw_path.resolve()

            if resolved.suffix.lower().lstrip(".") in self.SUPPORTED_FORMATS or (resolved.is_file() and not resolved.is_dir()):
                target_file = resolved
                target_folder = resolved.parent
                if resolved.suffix.lower().lstrip(".") in self.SUPPORTED_FORMATS:
                    format = resolved.suffix.lower().lstrip(".")
            else:
                target_folder = resolved
                target_file = target_folder / f"extracted_data.{format}"

            # Save extracted records
            output_path = self._save_dataframe(
                df=df,
                output_path=target_file,
                format=format
            )

            # Sync to alternate name (extract_data / extracted_data) if it exists or was empty
            for alt_name in ("extract_data", "extracted_data"):
                alt_path = target_folder / f"{alt_name}.{format}"
                if alt_path != output_path:
                    try:
                        self._save_dataframe(df=df, output_path=alt_path, format=format)
                    except Exception:
                        pass

            return {
                "success": True,
                "source_url": url,
                "records_extracted": len(df),
                "columns": df.columns.tolist(),
                "file_path": str(output_path),
                "format": format,
                "message": (
                    f"Successfully extracted {len(df)} records "
                    f"and saved them to {output_path}"
                )
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error_type": "timeout",
                "retryable": True,
                "message": "The request timed out."
            }

        except requests.exceptions.HTTPError as e:
            status_code = (
                e.response.status_code
                if e.response is not None
                else None
            )

            return {
                "success": False,
                "error_type": "http_error",
                "status_code": status_code,
                "retryable": status_code in {429, 500, 502, 503, 504},
                "message": str(e)
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error_type": "request_error",
                "retryable": True,
                "message": str(e)
            }

        except (ValueError, KeyError) as e:
            return {
                "success": False,
                "error_type": "parsing_error",
                "retryable": False,
                "message": str(e)
            }

        except Exception as e:
            return {
                "success": False,
                "error_type": "etl_error",
                "retryable": False,
                "message": str(e)
            }

    def transform_load_context(self, file_path: str) -> dict:
        """
        Read an existing CSV, JSON, or Parquet file and return
        a preview of its first three rows.
        """

        path = Path(file_path)

        if not path.is_absolute():
            path = self.project_root / path

        try:
            if not path.exists():
                return {
                    "success": False,
                    "error_type": "file_not_found",
                    "message": f"File does not exist: {path}"
                }

            extension = path.suffix.lower()

            if extension == ".csv":
                df = pd.read_csv(path)

            elif extension == ".json":
                df = pd.read_json(path)

            elif extension == ".parquet":
                df = pd.read_parquet(path)

            else:
                return {
                    "success": False,
                    "error_type": "unsupported_file_format",
                    "message": f"Unsupported file extension: {extension}"
                }

            return {
                "success": True,
                "file_path": str(path.resolve()),
                "total_rows": len(df),
                "columns": df.columns.tolist(),
                "preview": df.head(3).to_dict(orient="records")
            }

        except Exception as e:
            return {
                "success": False,
                "error_type": "file_read_error",
                "message": str(e)
            }

    def execute_code(self, code: str) -> str:
        """
        Execute python code (typically Pandas transformations).

        Args:
            code (str): The code to be executed.

        Returns:
            str: Output or status message of execution.
        """
        cleaned_code = code.strip()
        if "```" in cleaned_code:
            lines = cleaned_code.splitlines()
            code_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    code_lines.append(line)
            if code_lines:
                cleaned_code = "\n".join(code_lines)

        exec_globals = {
            "pd": pd,
            "pandas": pd,
            "os": os,
            "Path": Path,
            "requests": requests,
            "BeautifulSoup": BeautifulSoup,
            "__builtins__": __builtins__
        }

        try:
            exec(cleaned_code, exec_globals)
            return "Code executed successfully."
        except Exception as e:
            return f"Failed to execute code: {e}"


if __name__ == "__main__":
    etl = ETLTools()

    # Example 1: Extract a webpage into CSV.
    result = etl.extract_load(
        url=(
            "https://corporate.walmart.com/"
            "privacy-security/walmart-privacy-notice"
        ),
        output_folder="data/extract",
        format="csv"
    )

    print("Extraction result:")
    print(result)

    # Example 2: Read the extracted file.
    if result["success"]:
        preview = etl.transform_load_context(result["file_path"])
        print("\nFile preview:")
        print(preview)
