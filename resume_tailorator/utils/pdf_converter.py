from markdown_pdf import MarkdownPdf, Section


def markdown_to_pdf(
    markdown_content: str, output_path: str, css_style: str | None = None
) -> None:
    """
    Convert Markdown content to PDF with professional styling.

    Args:
        markdown_content: Raw Markdown text
        output_path: Path where PDF will be saved
        css_style: Optional CSS string for custom styling
    """
    # Create PDF generator with custom CSS
    pdf = MarkdownPdf(toc_level=2)

    # Add Markdown content as a section
    pdf.add_section(Section(markdown_content))

    # Save to output path
    pdf.save(output_path)
