# استخدام نسخة بايثون خفيفة جداً
FROM python:3.10-slim

# منع بايثون من كتابة ملفات .pyc وتوجيه السجلات مباشرة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ ملف المكاتب وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات البوت
COPY . .

# فتح المنفذ الذي سيستقبل الويب هوكس
EXPOSE 8080

# أمر تشغيل البوت
CMD ["python", "main.py"]