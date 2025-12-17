import streamlit as st
import os
import json
import csv
from datetime import datetime
import inflect
from docxtpl import DocxTemplate
from io import BytesIO

# ================= Configuration =================
TEMPLATE_FILE = "invoice.docx"
HISTORY_FILE = "invoice_history.csv"
STATE_FILE = "app_state.json"

RATE = 820.00
SGST_RATE = 0.09
CGST_RATE = 0.09

# ================= Helper Functions =================

def indian_format(n):
    """Numbers को 12,34,567.89 फॉर्मेट में बदलता है"""
    s, *d = str(f"{n:.2f}").partition(".")
    if len(s) > 3:
        s = s[:-3] + "," + s[-3:]
        i = len(s) - 6
        while i > 0:
            s = s[:i] + "," + s[i:]
            i -= 2
    return s + "".join(d)

def number_to_words(n):
    p = inflect.engine()
    words = p.number_to_words(n, andword="").title().replace("-", " ")
    return f"Rupees {words} Only"

def get_next_invoice_no(current_inv):
    if not current_inv:
        return "SBT/2526/1"
    try:
        parts = current_inv.rsplit('/', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"{parts[0]}/{int(parts[1]) + 1}"
    except:
        pass
    return current_inv

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(last_inv):
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_invoice": last_inv}, f)

def save_to_history(data_dict):
    file_exists = os.path.isfile(HISTORY_FILE)
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Invoice No", "Truck No", "Qty", "Amount", "Grand Total"])
        writer.writerow([
            data_dict['date'], 
            data_dict['invoice_no'], 
            data_dict['truck_no'], 
            data_dict['qty'], 
            data_dict['amount'], 
            data_dict['rounded']
        ])

# ================= Streamlit UI Layout =================

st.set_page_config(page_title="Invoice Generator", page_icon="🧾")

st.title("🧾 GST Invoice Generator")
st.markdown("### Laxmistuti Enterprises")

# --- Sidebar for Status ---
with st.sidebar:
    st.header("Settings & History")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "rb") as f:
            st.download_button("Download History CSV", f, file_name="invoice_history.csv")
    else:
        st.write("No history yet.")

# --- Load Last Invoice Number ---
saved_state = load_state()
last_inv = saved_state.get("last_invoice", "SBT/2526/0")
next_inv_suggestion = get_next_invoice_no(last_inv)

# --- Form Inputs ---
col1, col2 = st.columns(2)

with col1:
    inv_no = st.text_input("Invoice No:", value=next_inv_suggestion)
    truck_no = st.text_input("Truck No:", placeholder="MP09GH1234").upper()

with col2:
    date_val = st.text_input("Date:", value=datetime.today().strftime("%d/%m/%Y"))
    qty_val = st.number_input("Quantity (M.T.):", min_value=0.0, format="%.2f", step=0.1)

# --- Live Calculation & Preview ---
st.markdown("---")
st.subheader("Calculation Preview")

if qty_val > 0:
    amt = qty_val * RATE
    sgst = amt * SGST_RATE
    cgst = amt * CGST_RATE
    gtotal = amt + sgst + cgst
    rounded = round(gtotal)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Basic Amount", f"₹ {indian_format(amt)}")
    c2.metric("GST (18%)", f"₹ {indian_format(sgst + cgst)}")
    c3.metric("Grand Total", f"₹ {indian_format(rounded)}")
else:
    st.info("Enter quantity to see calculation.")

# --- Generate Button ---
if st.button("Generate Invoice", type="primary"):
    if not inv_no or not truck_no or qty_val <= 0:
        st.error("कृपया सभी डीटेल्स भरें और Quantity 0 से ज्यादा रखें।")
    else:
        # Data Preparation
        amt = qty_val * RATE
        sgst = amt * SGST_RATE
        cgst = amt * CGST_RATE
        gtotal = amt + sgst + cgst
        rounded = round(gtotal)

        context = {
            'invoice_no': inv_no,
            'date': date_val,
            'truck_no': truck_no,
            'qty': f"{qty_val:.2f}",
            'amount': indian_format(amt),
            'sgst': indian_format(sgst),
            'cgst': indian_format(cgst),
            'gtotal': indian_format(gtotal),
            'rounded': indian_format(rounded),
            'amount_words': number_to_words(rounded)
        }

        # Template Handling
        if not os.path.exists(TEMPLATE_FILE):
            st.error(f"Template '{TEMPLATE_FILE}' नहीं मिला! कृपया इसे उसी फोल्डर में रखें।")
        else:
            try:
                doc = DocxTemplate(TEMPLATE_FILE)
                doc.render(context)

                # Save to Memory buffer instead of disk directly
                io_stream = BytesIO()
                doc.save(io_stream)
                io_stream.seek(0)
                
                # Save History & State
                save_to_history(context)
                save_state(inv_no)
                
                st.success(f"Invoice {inv_no} Generated Successfully!")
                
                # Download Button
                file_name = f"Invoice_{inv_no.replace('/', '_')}.docx"
                st.download_button(
                    label="📥 Download Invoice File",
                    data=io_stream,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                st.info("अगले इनवॉइस के लिए पेज रिफ्रेश करें या नया नंबर डालें।")

            except Exception as e:
                st.error(f"Error: {e}")