"""Generate a printable e-ticket PDF for a confirmed booking using reportlab."""
import io
from decimal import Decimal

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)


PRIMARY = colors.HexColor('#4f46e5')
SECONDARY = colors.HexColor('#f59e0b')
DARK = colors.HexColor('#1f2937')
MUTED = colors.HexColor('#6b7280')
LIGHT = colors.HexColor('#f3f4f6')


def _styles():
    base = getSampleStyleSheet()
    styles = {
        'h1': ParagraphStyle('h1', parent=base['Heading1'], fontSize=22,
                             textColor=PRIMARY, leading=26, spaceAfter=4),
        'h2': ParagraphStyle('h2', parent=base['Heading2'], fontSize=14,
                             textColor=DARK, spaceBefore=10, spaceAfter=4),
        'body': ParagraphStyle('body', parent=base['BodyText'], fontSize=10,
                               textColor=DARK, leading=13),
        'muted': ParagraphStyle('muted', parent=base['BodyText'], fontSize=9,
                                textColor=MUTED, leading=12),
        'badge': ParagraphStyle('badge', fontSize=10, textColor=colors.white,
                                fontName='Helvetica-Bold', leading=12),
    }
    return styles


def generate_ticket_pdf(booking) -> bytes:
    """Return the PDF bytes for the given Booking."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"E-Ticket {booking.reference}",
    )
    S = _styles()
    story = []

    # ---- Header ----
    header_data = [[
        Paragraph("<b>✈ TravelGenie</b><br/><font size=9 color='#6b7280'>"
                  "AI-Powered Flight &amp; Hotel Booking</font>", S['body']),
        Paragraph(f"<para align='right'><font size=10 color='#6b7280'>E-TICKET</font><br/>"
                  f"<b><font size=14 color='#4f46e5'>{booking.reference}</font></b><br/>"
                  f"<font size=8 color='#6b7280'>{timezone.localtime(booking.created_at).strftime('%d %b %Y, %H:%M')}</font></para>",
                  S['body']),
    ]]
    header = Table(header_data, colWidths=[100 * mm, 70 * mm])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    story.append(Table([['']], colWidths=[170 * mm], rowHeights=[1.5],
                       style=[('BACKGROUND', (0, 0), (-1, -1), PRIMARY)]))
    story.append(Spacer(1, 8))

    # ---- Status badge ----
    status_color = {
        'confirmed': colors.HexColor('#22c55e'),
        'pending': colors.HexColor('#f59e0b'),
        'cancelled': colors.HexColor('#6b7280'),
        'completed': colors.HexColor('#3b82f6'),
    }.get(booking.status, colors.HexColor('#3b82f6'))

    badge = Table(
        [[Paragraph(f"<b>{booking.get_status_display().upper()}</b>", S['badge'])]],
        colWidths=[40 * mm], rowHeights=[7 * mm])
    badge.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(badge)
    story.append(Spacer(1, 10))

    # ---- Passenger / Guest ----
    user = booking.user
    story.append(Paragraph("Passenger / Guest", S['h2']))
    story.append(Paragraph(
        f"<b>{user.get_full_name() or user.username}</b><br/>"
        f"{user.email or '—'}", S['body']))
    story.append(Spacer(1, 8))

    # ---- Booking details ----
    if booking.booking_type == 'flight' and booking.flight:
        f = booking.flight
        story.append(Paragraph("Flight Details", S['h2']))
        info = [
            [Paragraph(f"<b>{f.airline}</b><br/><font size=9>{f.flight_number} · {f.aircraft}</font>", S['body']),
             Paragraph(f"<b>{f.get_cabin_class_display()}</b><br/><font size=9>{booking.passengers} passenger(s)</font>", S['body'])],
        ]
        t = Table(info, colWidths=[110 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

        route = [[
            Paragraph(f"<para align='center'><b><font size=18>{f.departure_time.strftime('%H:%M')}</font></b><br/>"
                      f"<font color='#4f46e5'><b>{f.origin}</b></font> ({f.origin_code})<br/>"
                      f"<font size=8 color='#6b7280'>{f.departure_time.strftime('%a, %d %b %Y')}</font></para>", S['body']),
            Paragraph(f"<para align='center'><font size=8 color='#6b7280'>{f.duration_str}</font><br/>"
                      f"<font color='#4f46e5'>━━ ✈ ━━</font></para>", S['body']),
            Paragraph(f"<para align='center'><b><font size=18>{f.arrival_time.strftime('%H:%M')}</font></b><br/>"
                      f"<font color='#4f46e5'><b>{f.destination}</b></font> ({f.destination_code})<br/>"
                      f"<font size=8 color='#6b7280'>{f.arrival_time.strftime('%a, %d %b %Y')}</font></para>", S['body']),
        ]]
        rt = Table(route, colWidths=[60 * mm, 50 * mm, 60 * mm])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(rt)
        story.append(Spacer(1, 8))

    elif booking.booking_type == 'hotel' and booking.hotel:
        h = booking.hotel
        story.append(Paragraph("Hotel Details", S['h2']))
        stars = '★' * h.star_rating + '☆' * (5 - h.star_rating)
        info = [
            [Paragraph(f"<b>{h.name}</b><br/><font size=9 color='#6b7280'>{h.city}, {h.country}</font><br/>"
                       f"<font color='#f59e0b'>{stars}</font>", S['body']),
             Paragraph(f"<b>{booking.rooms} room(s)</b><br/><font size=9>{booking.guests} guest(s)</font>", S['body'])],
        ]
        t = Table(info, colWidths=[110 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

        nights = booking.nights
        dates = [[
            Paragraph(f"<para align='center'><b>CHECK-IN</b><br/>"
                      f"<font size=14 color='#4f46e5'><b>{booking.check_in.strftime('%d %b %Y')}</b></font><br/>"
                      f"<font size=8 color='#6b7280'>{booking.check_in.strftime('%A')} · After 14:00</font></para>",
                      S['body']),
            Paragraph(f"<para align='center'><font size=8 color='#6b7280'>{nights} night(s)</font><br/>"
                      f"<font color='#4f46e5'>━━ 🌙 ━━</font></para>", S['body']),
            Paragraph(f"<para align='center'><b>CHECK-OUT</b><br/>"
                      f"<font size=14 color='#4f46e5'><b>{booking.check_out.strftime('%d %b %Y')}</b></font><br/>"
                      f"<font size=8 color='#6b7280'>{booking.check_out.strftime('%A')} · Before 11:00</font></para>",
                      S['body']),
        ]]
        dt = Table(dates, colWidths=[60 * mm, 50 * mm, 60 * mm])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(dt)
        story.append(Spacer(1, 8))

    # ---- Price summary ----
    story.append(Paragraph("Price Summary", S['h2']))
    rows = [
        ['Subtotal', f"₹{booking.subtotal or booking.total_amount:,.2f}"],
    ]
    if booking.discount_amount and booking.discount_amount > 0:
        rows.append([f"Discount ({booking.coupon_code or 'PROMO'})",
                     f"- ₹{booking.discount_amount:,.2f}"])
    if booking.loyalty_points_redeemed:
        rows.append([f"Loyalty redemption ({booking.loyalty_points_redeemed} pts)",
                     f"- ₹{booking.loyalty_points_redeemed:,.2f}"])
    if booking.has_insurance and booking.insurance_amount:
        rows.append([f"Travel insurance",
                     f"+ ₹{booking.insurance_amount:,.2f}"])
    rows.append(['Total paid', f"₹{booking.total_amount:,.2f}"])

    pt = Table(rows, colWidths=[120 * mm, 50 * mm])
    pt.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, 0), (-1, -2), DARK),
        ('LINEABOVE', (0, -1), (-1, -1), 0.5, MUTED),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -1), (1, -1), PRIMARY),
    ]))
    story.append(pt)
    story.append(Spacer(1, 10))

    # ---- Payment ----
    if hasattr(booking, 'payment'):
        p = booking.payment
        story.append(Paragraph("Payment", S['h2']))
        info = (f"<b>Transaction ID:</b> {p.transaction_id}<br/>"
                f"<b>Method:</b> {p.get_method_display()}"
                + (f" ending {p.card_last4}" if p.card_last4 else "") + "<br/>"
                f"<b>Status:</b> {p.get_status_display()}")
        story.append(Paragraph(info, S['body']))
        story.append(Spacer(1, 8))

    # ---- Footer ----
    story.append(Spacer(1, 14))
    story.append(Table([['']], colWidths=[170 * mm], rowHeights=[0.5],
                       style=[('BACKGROUND', (0, 0), (-1, -1), MUTED)]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This is a computer-generated e-ticket. Please carry a valid photo ID. "
        "Show this ticket at check-in. For support, contact "
        "<b>support@travelgenie.local</b>.",
        S['muted']))
    story.append(Paragraph(
        f"Issued by TravelGenie · {timezone.localtime().strftime('%d %b %Y, %H:%M')}",
        S['muted']))

    doc.build(story)
    return buf.getvalue()
