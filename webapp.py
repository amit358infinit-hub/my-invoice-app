import streamlit as st
import os
import inflect
from docxtpl import DocxTemplate
from docxcompose.composer import Composer
from docx import Document as Document_compose
from io import BytesIO

# ================= Configuration =================
TEMPLATE_FILE = "invoice.docx"
RATE = 820.00
SGST_RATE = 0.09
CGST_RATE = 0.09

# ================= Helper Functions =================
def indian_format(n):
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
    if not current_inv: return "SBT/2526/1"
    try:
        parts = current_inv.rsplit('/', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"{parts[0]}/{int(parts[1]) + 1}"
    except: pass
    return current_inv

# ================= Session State Init =================
# यह लिस्ट "Add" किए गए इनवॉइस को याद रखेगी
if 'invoice_queue' not in st.session_state:
    st.session_state.invoice_queue = []

if 'last_inv_no' not in st.session_state:
    st.session_state.last_inv_no = "SBT/2526/1"

# ================= UI Layout =================
st.set_page_config(page_title="Multi-Invoice Generator", page_icon="📑")
st.title("📑 Multi-Invoice Generator")
st.markdown("### Laxmistuti Enterprises")

# --- Form Inputs ---
col1, col2 = st.columns(2)
with col1:
    # अगर पिछले इनवॉइस से अगला नंबर है तो वो दिखाएं
    inv_no = st.text_input("Invoice No:", value=st.session_state.last_inv_no)
    truck_no = st.text_input("Truck No:", placeholder="MP09GH1234").upper()
with col2:
    date_val = st.text_input("Date:", value="11/12/2025") # Default date
    qty_val = st.number_input("Quantity (M.T.):", min_value=0.0, format="%.2f", step=0.1)

# --- Calculation ---
amt = qty_val * RATE
sgst = amt * SGST_RATE
cgst = amt * CGST_RATE
gtotal = amt + sgst + cgst
rounded = round(gtotal)

if qty_val > 0:
    st.info(f"Amount: {indian_format(rounded)} | Words: {number_to_words(rounded)}")

# ================= ACTION BUTTONS =================

# 1. ADD TO LIST BUTTON
if st.button("➕ Add Invoice to List", type="primary"):
    if not inv_no or not truck_no or qty_val <= 0:
        st.error("Please fill all details correctly.")
    else:
        # Context create karein
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
        
        # Queue me add karein
        st.session_state.invoice_queue.append(context)
        st.success(f"✅ Invoice {inv_no} added! (Total in list: {len(st.session_state.invoice_queue)})")
        
        # Agla invoice number set karein
        next_no = get_next_invoice_no(inv_no)
        st.session_state.last_inv_no = next_no
        st.rerun() # Page refresh taaki naya number dikhe

st.markdown("---")

# ================= QUEUE DISPLAY & DOWNLOAD =================

if len(st.session_state.invoice_queue) > 0:
    st.subheader(f"📋 Invoices Ready to Print ({len(st.session_state.invoice_queue)})")
    
    # List dikhayein
    for i, item in enumerate(st.session_state.invoice_queue):
        st.text(f"{i+1}. Inv: {item['invoice_no']} | Truck: {item['truck_no']} | Amt: {item['rounded']}")

    col_d1, col_d2 = st.columns([1, 1])

    # 2. GENERATE COMBINED FILE
    with col_d1:
        if st.button("📥 Generate Combined Word File"):
            if not os.path.exists(TEMPLATE_FILE):
                st.error("Template file not found!")
            else:
                try:
                    # Master Composer setup
                    master_doc = None
                    composer = None

                    # Har saved context ke liye loop chalayein
                    for idx, ctx in enumerate(st.session_state.invoice_queue):
                        doc = DocxTemplate(TEMPLATE_FILE)
                        doc.render(ctx)

                        if idx == 0:
                            # Pehla invoice master banega
                            # Hame ise memory me save karke wapas load karna padega
                            # taaki wo 'Document' object ban jaye 'DocxTemplate' se
                            temp_io = BytesIO()
                            doc.save(temp_io)
                            temp_io.seek(0)
                            master_doc = Document_compose(temp_io)
                            composer = Composer(master_doc)
                        else:
                            # Agle invoices append honge
                            master_doc.add_page_break() # Naya page
                            
                            temp_io = BytesIO()
                            doc.save(temp_io)
                            temp_io.seek(0)
                            sub_doc = Document_compose(temp_io)
                            composer.append(sub_doc)

                    # Final save to memory
                    final_io = BytesIO()
                    composer.save(final_io)
                    final_io.seek(0)

                    st.session_state['final_file'] = final_io
                    st.success("File Created! Click Download below.")

                except Exception as e:
                    st.error(f"Error: {e}")

    # 3. DOWNLOAD BUTTON (Generate hone ke baad dikhega)
    if 'final_file' in st.session_state:
        st.download_button(
            label="⬇️ Download All Invoices (DOCX)",
            data=st.session_state['final_file'],
            file_name="Combined_Invoices.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # 4. CLEAR LIST
    with col_d2:
        if st.button("🗑️ Clear List"):
            st.session_state.invoice_queue = []
            if 'final_file' in st.session_state:
                del st.session_state['final_file']
            st.rerun()

else:
    st.info("👆 ऊपर डिटेल्स भरकर 'Add Invoice' बटन दबाएं। लिस्ट यहाँ दिखेगी।")
