"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Đã được định nghĩa mẫu sẵn cho Học viên tham khảo
    {
        "name": "academic_query",
        "description": "Tra cứu hồ sơ và thông tin học vụ của sinh viên VinUni bằng mã sinh viên.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần tra cứu (ví dụ: 'SV2026001')"
                }
            },
            "required": ["student_id"]
        }
    },
    
    {
        "name": "schedule_appointment",
        "description": "Đặt lịch hẹn tư vấn học vụ với Cố vấn học tập VinUni.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần đặt lịch (ví dụ: 'SV2026001')."
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian hẹn (ví dụ: '14:00 15/09/2026')."
                },
                "advisor_name": {
                    "type": "string",
                    "description": "Tên cố vấn học tập phụ trách buổi tư vấn."
                }
            },
            "required": ["student_id", "datetime_str", "advisor_name"]
        }
    },
    {
        "name": "exam_schedule_query",
        "description": "Tra cứu lịch thi của sinh viên VinUni theo mã sinh viên và mã môn học tùy chọn.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần tra cứu lịch thi (ví dụ: 'SV2026001')."
                },
                "course_code": {
                    "type": "string",
                    "description": "Mã môn học cần tra cứu, bỏ trống để lấy toàn bộ lịch thi."
                }
            },
            "required": ["student_id"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "SV2026001": {
        "full_name": "Nguyễn Văn An",
        "class": "AI-K4",
        "gpa": 3.85,
        "email": "an.nv@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "PGS.TS Nguyễn Văn A"
    },
    "SV2026002": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.60,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B"
    }
}

MOCK_EXAM_SCHEDULE = {
    "SV2026001": [
        {
            "course_code": "AI201",
            "course_name": "Lập trình Python nâng cao",
            "datetime": "08:00 20/12/2026",
            "room": "C304",
            "format": "Tự luận"
        },
        {
            "course_code": "AI202",
            "course_name": "Học máy cơ bản",
            "datetime": "13:30 22/12/2026",
            "room": "A201",
            "format": "Trên máy tính"
        }
    ],
    "SV2026002": [
        {
            "course_code": "AI201",
            "course_name": "Lập trình Python nâng cao",
            "datetime": "08:00 20/12/2026",
            "room": "C305",
            "format": "Tự luận"
        }
    ]
}


def execute_academic_query(student_id: str) -> str:
    """Thực thi tra cứu học vụ theo mã sinh viên"""
    student = MOCK_DATABASE.get(student_id.strip().upper())
    if student:
        return json.dumps({
            "status": "SUCCESS",
            "student_id": student_id,
            "data": student
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy dữ liệu sinh viên có mã '{student_id}'"
        }, ensure_ascii=False)


def execute_schedule_appointment(
    student_id: str = "", datetime_str: str = "", advisor_name: str = ""
) -> str:
    """Thực thi đặt lịch hẹn tư vấn học vụ"""
    fields = {
        "student_id": student_id,
        "datetime_str": datetime_str,
        "advisor_name": advisor_name,
    }
    missing_fields = [name for name, value in fields.items() if not str(value).strip()]
    if missing_fields:
        return json.dumps({
            "status": "VALIDATION_ERROR",
            "missing_fields": missing_fields,
            "message": "Thiếu thông tin bắt buộc để đặt lịch."
        }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"BK-{student_id}-99",
        "student_id": student_id,
        "datetime": datetime_str,
        "advisor": advisor_name,
        "message": f"Đặt lịch thành công cho sinh viên {student_id} với {advisor_name} vào lúc {datetime_str}."
    }, ensure_ascii=False)


def execute_exam_schedule_query(student_id: str, course_code: str = "") -> str:
    """Tra cứu lịch thi theo sinh viên và tùy chọn lọc theo mã môn học."""
    normalized_student_id = student_id.strip().upper()
    exams = MOCK_EXAM_SCHEDULE.get(normalized_student_id)
    if not exams:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy lịch thi của sinh viên có mã '{student_id}'"
        }, ensure_ascii=False)

    if course_code:
        normalized_course_code = course_code.strip().upper()
        exams = [exam for exam in exams if exam["course_code"] == normalized_course_code]
        if not exams:
            return json.dumps({
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy lịch thi môn '{course_code}' của sinh viên {normalized_student_id}"
            }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "student_id": normalized_student_id,
        "data": exams
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "academic_query": execute_academic_query,
    "schedule_appointment": execute_schedule_appointment,
    "exam_schedule_query": execute_exam_schedule_query
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
