from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_pdf(invoice):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", size=12)
    # can.drawString(100, 600, "x100")
    # can.drawString(200, 600, "x200")
    # can.drawString(300, 600, "x300")
    # can.drawString(400, 600, "x400")
    # can.drawString(500, 600, "x500")
    # can.drawString(10, 100, "x100")
    # can.drawString(10, 200, "x200")
    # can.drawString(10, 300, "x300")
    # can.drawString(10, 400, "x400")
    # can.drawString(10, 500, "x500")
    # can.drawString(10, 600, "x600")
    can.drawString(135, 646, str(invoice.id))
    can.drawString(415, 646, str(invoice.created.strftime("%b %d, %Y")))
    can.drawString(115, 619, str(invoice.client.ca_first_name) + ' ' + str(invoice.client.ca_last_name))
    height = 500
    item = 1
    package = invoice.price_breakdown.get("package")
    if package:
        print("if")
        can.drawString(75, height, str(item))
        can.drawString(120, height, package.get("name"))
        can.drawString(410, height, "1")
        can.drawString(480, height, str(package.get("price")))
        height -= 25
        item += 1
    senior_managers = invoice.price_breakdown.get("senior_managers")
    if senior_managers:
        print("if 2")
        can.drawString(75, height, str(item))
        can.drawString(120, height, senior_managers[0])
        can.drawString(410, height, senior_managers[2].split()[0])
        can.drawString(480, height, str(senior_managers[1]))
        height -= 75
        item += 1
    hiring_managers = invoice.price_breakdown.get("hiring_managers")
    if hiring_managers:
        print("if 2")
        can.drawString(75, height, str(item))
        can.drawString(150, height, hiring_managers[0])
        can.drawString(410, height, hiring_managers[2].split()[0])
        can.drawString(480, height, str(hiring_managers[1]))
        height -= 75
        item += 1
    hiring_team_member = invoice.price_breakdown.get("hiring_team_member")
    if hiring_team_member:
        print("if 2")
        can.drawString(75, height, str(item))
        can.drawString(150, height, hiring_team_member[0])
        can.drawString(410, height, hiring_team_member[2].split()[0])
        can.drawString(480, height, str(hiring_team_member[1]))
        height -= 75
        item += 1
    # can.drawString(75, 475, "Item 2")
    # can.drawString(150, 475, "Item 2 long description is some good")
    total = invoice.price_breakdown.get("total")
    if total:
        can.setFont("Helvetica-Bold", 24)
        can.drawString(300, 225, "Total")
        can.drawString(400, 225, str(total.get("amount", invoice.amount)))
        can.setFont("Helvetica", 12)
        can.drawString(300, 200, "(For {} days.)".format(total.get("days", 30)))
    else:
        can.setFont("Helvetica-Bold", 24)
        can.drawString(300, 225, "Total")
        can.drawString(400, 225, str(invoice.amount))
        can.drawString(300, 200, "(For {} days.)".format(30))
        
    can.save()

    #move to the beginning of the StringIO buffer
    packet.seek(0)

    # create a new PDF with Reportlab
    new_pdf = PdfReader(packet)
    # read your existing PDF
    existing_pdf = PdfReader(open("static/invoice.pdf", "rb"))
    output = PdfWriter()
    # add the "watermark" (which is the new pdf) on the existing page
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)
    # finally, write "output" to a real file
    output_stream = open("invoice.pdf", "wb")
    output.write(output_stream)
    output_stream.close()

# generate_pdf("hi")