import nbformat
from nbconvert import MarkdownExporter
from nbconvert.writers import FilesWriter
from traitlets.config import Config

from pathlib import Path
import shutil
import os
from rich.progress import track

import json
import sys
from binascii import a2b_base64
from mimetypes import guess_extension
from textwrap import dedent

from traitlets import Set, Unicode

from nbconvert.preprocessors import Preprocessor


def guess_extension_without_jpe(mimetype):
    """Fixes a problem with '.jpe' extension of jpeg images which are not recognised by latex.

    For any other case, the function works in the same way
    as mimetypes.guess_extension.
    """
    ext = guess_extension(mimetype)
    if ext == ".jpe":
        ext = ".jpeg"
    return ext


def platform_utf_8_encode(data):
    """Encode data based on platform."""
    if isinstance(data, str):
        if sys.platform == "win32":
            data = data.replace("\n", "\r\n")
        data = data.encode("utf-8")
    return data


class ExtractOutputPreprocessor(Preprocessor):
    """Extracts all the outputs from the notebook file.

    The extracted outputs are returned in the 'resources' dictionary.
    """

    output_filename_template = Unicode("{notebook_title}_{cell_index}_{index}{extension}").tag(config=True)

    extract_output_types = Set({"image/png", "image/jpeg", "image/svg+xml", "application/pdf"}).tag(config=True)

    def preprocess(self, nb, resources):
        """Preprocessing to apply on each notebook.

        Must return modified nb, resources.

        If you wish to apply your preprocessing to each cell, you might want
        to override preprocess_cell method instead.

        Parameters
        ----------
        nb : NotebookNode
            Notebook being converted
        resources : dictionary
            Additional resources used in the conversion process.  Allows
            preprocessors to pass variables into the Jinja engine.
        """
        notebook_title = nb["metadata"]["title"]

        for index, cell in enumerate(nb.cells):
            nb.cells[index], resources = self.preprocess_cell(
                cell=cell, resources=resources, cell_index=index, notebook_title=notebook_title
            )
        return nb, resources

    def preprocess_cell(self, cell, resources, cell_index, notebook_title):
        """Apply a transformation on each cell,.

        Parameters
        ----------
        cell : NotebookNode cell
            Notebook cell being processed
        resources : dictionary
            Additional resources used in the conversion process.  Allows
            preprocessors to pass variables into the Jinja engine.
        cell_index : int
            Index of the cell being processed (see base.py)
        """
        # Get the unique key from the resource dict if it exists.  If it does not
        # exist, use 'output' as the default.  Also, get files directory if it
        # has been specified
        unique_key = resources.get("unique_key", "output")
        output_files_dir = resources.get("output_files_dir", f"{notebook_title}_files/")

        # Make sure outputs key exists
        if not isinstance(resources["outputs"], dict):
            resources["outputs"] = {}

        # Loop through all of the outputs in the cell
        for index, out in enumerate(cell.get("outputs", [])):
            if out.output_type not in {"display_data", "execute_result"}:
                continue
            if "text/html" in out.data:
                out["data"]["text/html"] = dedent(out["data"]["text/html"])
            # Get the output in data formats that the template needs extracted
            for mime_type in self.extract_output_types:
                if mime_type in out.data:
                    data = out.data[mime_type]

                    # Binary files are base64-encoded, SVG is already XML
                    if mime_type in {"image/png", "image/jpeg", "application/pdf"}:
                        # data is b64-encoded as text (str, unicode),
                        # we want the original bytes
                        data = a2b_base64(data)
                    elif mime_type == "application/json" or not isinstance(data, str):
                        # Data is either JSON-like and was parsed into a Python
                        # object according to the spec, or data is for sure
                        # JSON. In the latter case we want to go extra sure that
                        # we enclose a scalar string value into extra quotes by
                        # serializing it properly.
                        if isinstance(data, bytes):
                            # We need to guess the encoding in this
                            # instance. Some modules that return raw data like
                            # svg can leave the data in byte form instead of str
                            data = data.decode("utf-8")
                        data = platform_utf_8_encode(json.dumps(data))
                    else:
                        # All other text_type data will fall into this path
                        data = platform_utf_8_encode(data)

                    ext = guess_extension_without_jpe(mime_type)
                    if ext is None:
                        ext = "." + mime_type.rsplit("/")[-1]
                    if out.metadata.get("filename", ""):
                        filename = out.metadata["filename"]
                        if not filename.endswith(ext):
                            filename += ext
                    else:
                        filename = self.output_filename_template.format(
                            unique_key=unique_key,
                            cell_index=cell_index,
                            index=index,
                            extension=ext,
                            notebook_title=notebook_title,
                        )

                    # On the cell, make the figure available via
                    #   cell.outputs[i].metadata.filenames['mime/type']
                    # where
                    #   cell.outputs[i].data['mime/type'] contains the data
                    if output_files_dir is not None:
                        filename = os.path.join(output_files_dir, filename)
                    out.metadata.setdefault("filenames", {})
                    out.metadata["filenames"][mime_type] = filename

                    if filename in resources["outputs"]:
                        msg = (
                            "Your outputs have filename metadata associated "
                            "with them. Nbconvert saves these outputs to "
                            "external files using this filename metadata. "
                            "Filenames need to be unique across the notebook, "
                            f"or images will be overwritten. The filename {filename} is "
                            "associated with more than one output. The second "
                            "output associated with this filename is in cell "
                            f"{cell_index}."
                        )
                        raise ValueError(msg)
                    # In the resources, make the figure available via
                    #   resources['outputs']['filename'] = data
                    resources["outputs"][filename] = data

        return cell, resources


tutorials = [f.name for f in os.scandir() if f.is_dir() and "." not in f.name and f.name == "four_nations"]

for tutorial in track(tutorials):
    # Load a notebook as nbformat.NotebookNode using its path
    source_directory = Path(f"./{tutorial}")
    output_charts_directory = source_directory / "charts"

    if not output_charts_directory.exists():
        output_charts_directory.mkdir()

    tutorial_path = source_directory / f"{tutorial}.ipynb"
    nb_node = nbformat.read(tutorial_path, nbformat.NO_CONVERT)

    if tutorial == "xg_scatters":
        output_name = "forward_lines"

    elif tutorial == "rink_maps":
        output_name = "shot_maps"

    else:
        output_name = tutorial

    nb_node["metadata"]["title"] = output_name

    os.chdir(source_directory)

    c = Config()

    output_processor = ExtractOutputPreprocessor(config=c)

    c.FilesWriter.build_directory = "."
    c.MarkdownExporter.preprocessors = [
        "nbconvert.preprocessors.ExecutePreprocessor",
        output_processor,
        # "nbconvert.preprocessors.ExtractOutputPreprocessor",
    ]

    me = MarkdownExporter(config=c)
    (output, resources) = me.from_notebook_node(nb_node)

    # Employ nbconvert.writers.FilesWriter to write the markdown file
    fw = FilesWriter(config=c)
    fw.write(output, resources, notebook_name=output_name)

    os.chdir("../")

    destination_directory = Path("../../docs/guide/tutorials")
    markdown_file = f"{output_name}.md"

    shutil.move(Path(source_directory / markdown_file), Path(destination_directory / markdown_file))

    for file_path in (destination_directory / f"{output_name}_files").glob("*.png"):
        if file_path.is_file():
            file_path.unlink()

    for file_path in (source_directory / f"{output_name}_files").glob("*.png"):
        if file_path.is_file():
            # Create the destination path for the file
            file_name = file_path.name.replace("output", output_name)
            new_file_path = destination_directory / f"{output_name}_files" / file_name
            # Move the file
            shutil.move(file_path, new_file_path)

    for file_path in source_directory.glob("*.html"):
        if file_path.is_file():
            # Create the destination path for the file
            file_name = file_path.name.replace("output", output_name)
            new_file_path = destination_directory / f"{output_name}_files" / file_name
            # Move the file
            shutil.move(file_path, new_file_path)

    for file_path in source_directory.glob("*"):
        if file_path.is_file():
            if "ipynb" not in file_path.name:
                file_path.unlink()

    example_charts_directory = Path("../../docs/guide/examples/images")
    example_charts = [x.name for x in example_charts_directory.glob("*.png")]

    output_charts = output_charts_directory.glob("*.png")

    if tutorial == "lollipop":
        latest_game = max([int(x.name.replace(".png", "")) for x in output_charts_directory.glob("*.png")])
        latest_game = f"{latest_game}.png"

    for output_chart in output_charts:
        if output_chart.name in example_charts:
            shutil.copy2(output_chart, example_charts_directory)

        if tutorial == "lollipop" and output_chart.name == latest_game:
            shutil.copy2(output_chart, example_charts_directory / "nsh_lollipop.png")

    shutil.rmtree(output_charts_directory)
    shutil.rmtree(source_directory / f"{output_name}_files")
