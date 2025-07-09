from flask import Flask, render_template, request
import datetime
import os

from flask import Response
import requests

app = Flask(__name__)

BLOCKLIST_FILE = 'blocklist.txt'
study_time = {"start": None, "end": None}

def is_site_exists(site):
    # Đảm bảo có http hoặc https
    if not site.startswith('http'):
        url = 'http://' + site
    else:
        url = site
    try:
        # Sử dụng HEAD cho nhanh, thử GET nếu HEAD bị chặn
        response = requests.head(url, timeout=3, allow_redirects=True)
        if response.status_code < 400:
            return True
        # Một số web không cho HEAD, thử GET
        response = requests.get(url, timeout=3, allow_redirects=True)
        return response.status_code < 400
    except requests.RequestException:
        return False


def is_within_time_range(start, end, now):
    if start < end:
        return start <= now <= end
    else:
        return now >= start or now <= end


def load_blocked_sites():
    if os.path.exists(BLOCKLIST_FILE):
        with open(BLOCKLIST_FILE, 'r') as f:
            return list(set([s.strip() for s in f.readlines() if s.strip()]))
    return []


def save_blocked_sites(sites):
    with open(BLOCKLIST_FILE, 'w') as f:
        f.write('\n'.join(sites))

def is_blocked(url):
    with open("blocklist.txt", 'r') as f:
        blocked_sites = [line.strip() for line in f.readlines() if line.strip()]
    for site in blocked_sites:
        if site in url:
            return True
    return False
import re

def is_valid_url(site):
    # Kiểm tra domain hoặc URL có dạng hợp lệ
    pattern = re.compile(
        r'^(https?:\/\/)?'            # http:// hoặc https:// (không bắt buộc)
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # domain dạng abc.com hoặc www.abc.vn
        r'(\/.*)?$'                   # phần path (nếu có)
    )
    return pattern.match(site) is not None



@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    blocked_sites = load_blocked_sites()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'set_time':
            study_time['start'] = request.form['start_time']
            study_time['end'] = request.form['end_time']
            message = '🕒 Đã cập nhật thời gian học.'

        elif action == 'add_site':
            site = request.form['site_to_add'].strip()
            if not is_valid_url(site):
                message = f'⚠️ Địa chỉ "{site}" không hợp lệ. Vui lòng nhập đúng định dạng (ví dụ: facebook.com hoặc https://abc.xyz).'
            elif site in blocked_sites:
                message = f'⚠️ Địa chỉ "{site}" đã có trong danh sách chặn.'
            elif not is_site_exists(site):
                message = f'⚠️ Website "{site}" không tồn tại. Vui lòng kiểm tra lại tên miền!'
            else:
                blocked_sites.append(site)
                save_blocked_sites(blocked_sites)
                message = f'➕ Đã thêm "{site}" vào danh sách chặn.'

        elif action == 'delete_site':
            site = request.form['site_to_delete'].strip()
            if site in blocked_sites:
                blocked_sites.remove(site)
                save_blocked_sites(blocked_sites)
                message = f'❌ Đã xóa "{site}" khỏi danh sách chặn.'

    return render_template('index.html', message=message, study_time=study_time, blocked_sites=blocked_sites)


@app.route('/check/<path:url>')
def check_url(url):
    if not study_time['start'] or not study_time['end']:
        return "Thời gian học chưa được thiết lập.", 400

    now = datetime.datetime.now().time()
    start = datetime.datetime.strptime(study_time['start'], "%H:%M").time()
    end = datetime.datetime.strptime(study_time['end'], "%H:%M").time()
    blocked_sites = load_blocked_sites()

    for site in blocked_sites:
        if site in url and is_within_time_range(start, end, now):
            return f"TRUY CẬP BỊ CHẶN: {site}", 403
    return f"ĐƯỢC PHÉP TRUY CẬP: {url}"

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "⚠️ Thiếu URL (?url=http...)", 400

    # Chỉ chặn nếu trong giờ học
    if is_blocked(target_url):
        if study_time['start'] and study_time['end']:
            now = datetime.datetime.now().time()
            start = datetime.datetime.strptime(study_time['start'], "%H:%M").time()
            end = datetime.datetime.strptime(study_time['end'], "%H:%M").time()
            if is_within_time_range(start, end, now):
                return render_template("blocked.html", blocked_url=target_url)
    # Nếu ngoài giờ học, vẫn truy cập bình thường

    try:
        r = requests.get(target_url)
        return Response(r.content, content_type=r.headers.get('Content-Type', 'text/html'))
    except Exception as e:
        return f"Lỗi khi truy cập trang: {e}", 500


if __name__ == "__main__":
    app.run(debug=True)
