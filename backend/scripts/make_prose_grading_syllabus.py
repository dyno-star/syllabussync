from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_prose_grading_syllabus(path: str):
    """
    Real bug found in production: syllabi that phrase grading weights as
    prose ("X is worth Y%", "X counts for Y%") rather than "X: Y%" caused
    the name-capture regex to swallow the filler words into the assignment
    name (e.g. "Recitation is worth" instead of "Recitation"). This fixture
    exists to lock in the fix in rule_based_extraction.clean_extracted_name.
    """
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 72

    def line(text, size=11, gap=16):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(72, y, text)
        y -= gap

    line("PHYS 101: Introduction to Physics", size=14, gap=24)
    line("Grading", size=12, gap=20)
    line("Recitation is worth 10% of your final grade.")
    line("Final Exam is worth 20% of your final grade.")
    line("Attendance counts for 5% of your final grade.")
    line("Homework accounts for 10% of your final grade.")

    c.save()


if __name__ == "__main__":
    make_prose_grading_syllabus("app/eval/fixtures/prose_grading_phys101.pdf")
    print("Wrote app/eval/fixtures/prose_grading_phys101.pdf")
