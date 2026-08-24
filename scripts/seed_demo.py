from datetime import datetime
from app.services.database import connect

EMPLOYEES = [
    ("NV001","Nguyễn An","HHP","Sản xuất","Kỹ thuật viên",50000,7000000),
    ("NV002","Trần Bình","SBC","Kinh doanh","Nhân viên",65000,8000000),
    ("NV003","Lê Chi","HHP","Kế toán","Kế toán viên",70000,9000000),
]

conn=connect()
for emp_id,name,company,department,title,rate,insurance in EMPLOYEES:
    conn.execute("INSERT OR IGNORE INTO employees(employee_id,full_name,company,department,job_title,start_date,insurance_salary,social_insurance,health_insurance,unemployment_insurance,bank_account,bank_name) VALUES(?,?,?,?,?,'2026-01-01',?,1,1,1,?,?)",(emp_id,name,company,department,title,insurance,"000"+emp_id[-3:],"Ngân hàng mẫu"))
    conn.execute("INSERT OR IGNORE INTO salary_history(employee_id,hourly_rate,effective_from,created_at) VALUES(?,?,?,?)",(emp_id,rate,"2026-01-01",datetime.now().isoformat()))
conn.commit()
print("Đã tạo 3 nhân viên mẫu.")

