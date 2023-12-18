import fitz
import re
import scrapy
from scrapy.crawler import CrawlerProcess


# parse pdf file and return text
def get_pdf_content(uploaded_file):
    # Read the PDF file and extract the text content
    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf",
    )
    text_content = ""

    for page in pdf_document:
        text_content += page.get_text()

    # Handle special characters and bullet points using regular expressions
    text_content = re.sub(r"\s+([•●▪▸*-])\s+", r" \1 ", text_content)
    text_content = re.sub(r"\s+([,.:;?!(){}\[\]])\s+", r"\1 ", text_content)

    return text_content


def prompt_ai_using_form_fields():
    # Define the custom prompts to get specific information
    prompts = {
        "Name ": "Please extract the name of the person applying from this resume.",
        "Contact 📱 📧": "Please extract the contact details (phone number and email) from the resume.",
        "Experience 👨🏽‍💻👩🏼‍🔬": "Please extract the work experience details from the resume and format properly.",
        "Education 🎓": "Please extract the education details from the resume and format properly.",
        "Skills 🤹🏻‍♂️🦸🏾‍♀️": "Please extract the skills details from the resume.",
        "Links 👾": "Please extract the links like github, personal website, linkedin details from the resume.",
        # "Cover Letter": "Please create a cover letter based on the resume and {} if a job description is provided below".format(
        #     job_descr
        # ),
    }
