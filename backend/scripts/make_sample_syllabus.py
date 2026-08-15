"""
Generates a synthetic sample syllabus PDF for testing the extraction pipeline.

This is NOT meant to be a permanent fixture generator for the real eval set —
real eval fixtures should come from actual (anonymized) syllabi. This just
gives us something realistic to develop against before we have real samples.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_sample_syllabus(path: str):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 72

    def line(text, size=11, gap=16):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(72, y, text)
        y -= gap

    line("CS 260: Data Structures and Algorithms", size=14, gap=24)
    line("Instructor: Dr. Alan Reyes")
    line("Term: Fall 2026")
    line("")
    line("Course Description", size=12, gap=20)
    line("This course covers fundamental data structures and algorithm design.")
    line("")
    line("Grading Breakdown", size=12, gap=20)
    line("Homework Assignments: 20%")
    line("Midterm Exam: 25%")
    line("Final Exam: 30%")
    line("Course Project: 20%")
    line("Class Participation: 5%")
    line("")
    line("Schedule", size=12, gap=20)
    line("Homework 1 due September 15, 2026")
    line("Midterm Exam on October 20, 2026")
    line("Homework 2 due November 3, 2026")
    line("Course Project due December 1, 2026")
    line("Final Exam on December 15, 2026")
    line("")
    line("Late Policy", size=12, gap=20)
    line("Late homework submissions lose 10% per day, up to 3 days late.")

    c.save()


if __name__ == "__main__":
    make_sample_syllabus("app/eval/fixtures/sample_cs260.pdf")
    print("Wrote app/eval/fixtures/sample_cs260.pdf")
