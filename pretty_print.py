import io
from typing import List


def pretty_print_table(headers: List[str], data: List[List[str]]) -> str:
    # Get the maximum length of each column
    max_lengths = [len(header) for header in headers]
    for row in data:
        for i in range(len(headers)):
            max_lengths[i] = max(max_lengths[i], len(str(row[i])))

    # Print the headers
    column_separator = " | "
    with io.StringIO() as string_builder:
        string_builder.write(column_separator.join(headers[i].ljust(max_lengths[i]) for i in range(len(headers))))
        string_builder.write("\n")
        string_builder.write("-" * (sum(max_lengths) + (len(headers) - 1) * len(column_separator)))
        string_builder.write("\n")

        # Print the data rows
        for row in data:
            string_builder.write(column_separator.join(str(row[i]).ljust(max_lengths[i]) for i in range(len(headers))))
            string_builder.write("\n")

        return string_builder.getvalue()