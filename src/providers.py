"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        context = context or []
        latest_observation = context[-1].get("result", {}) if context else {}

        if latest_observation.get("status") == "NOT_FOUND":
            return {
                "type": "text",
                "content": latest_observation.get("message", "Không tìm thấy thông tin sinh viên yêu cầu."),
                "thought": "Kết quả tra cứu không có dữ liệu, nên trả lời chính xác theo Observation."
            }

        if latest_observation.get("status") == "SUCCESS" and "booking_id" in latest_observation:
            return {
                "type": "text",
                "content": latest_observation.get("message", "Đặt lịch tư vấn thành công."),
                "thought": "Lịch hẹn đã được tạo thành công, tôi trả lời kết quả cuối cùng."
            }

        if latest_observation.get("status") == "SUCCESS" and context[-1].get("tool_name") == "exam_schedule_query":
            exams = latest_observation.get("data", [])
            schedule_lines = [
                f"- {exam['course_code']} ({exam['course_name']}): {exam['datetime']}, phòng {exam['room']}, {exam['format']}"
                for exam in exams
            ]
            return {
                "type": "text",
                "content": "Lịch thi của sinh viên " + latest_observation.get("student_id", "") + ":\n" + "\n".join(schedule_lines),
                "thought": "Tôi tổng hợp lịch thi từ Observation mà không bổ sung dữ liệu ngoài tool."
            }

        if latest_observation.get("status") == "SUCCESS" and context[-1].get("tool_name") == "class_schedule_query":
            classes = latest_observation.get("data", [])
            schedule_lines = [
                f"- {item['weekday']}: {item['course_code']} ({item['course_name']}), {item['time']}, phòng {item['room']}, giảng viên {item['instructor']}"
                for item in classes
            ]
            return {
                "type": "text",
                "content": "Lịch học của sinh viên " + latest_observation.get("student_id", "") + ":\n" + "\n".join(schedule_lines),
                "thought": "Tôi tổng hợp lịch học từ Observation mà không bổ sung dữ liệu ngoài tool."
            }

        if latest_observation.get("status") == "SUCCESS" and "data" in latest_observation:
            if "đặt lịch" not in prompt_lower:
                student = latest_observation["data"]
                return {
                    "type": "text",
                    "content": (
                        f"Kết quả tra cứu cho sinh viên {latest_observation.get('student_id', '')} "
                        f"({student.get('full_name', '')}): Lớp {student.get('class', '')}, "
                        f"GPA: {student.get('gpa', '')}, Cố vấn: {student.get('advisor', '')}."
                    ),
                    "thought": "Yêu cầu chỉ là tra cứu, tôi tổng hợp kết quả từ Observation."
                }
            if not re.search(r"\b\d{1,2}:\d{2}\b", prompt):
                return {
                    "type": "text",
                    "content": "Để đặt lịch, vui lòng cung cấp thời gian hẹn cụ thể.",
                    "thought": "Đã có cố vấn từ Observation nhưng chưa có thời gian hẹn."
                }
            advisor = latest_observation["data"].get("advisor", "PGS.TS Nguyễn Văn A")
            student_id = latest_observation.get("student_id", "SV2026001")
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {
                    "student_id": student_id,
                    "datetime_str": "14:00 15/09/2026",
                    "advisor_name": advisor
                },
                "thought": "Đã xác định được cố vấn từ hồ sơ học vụ. Tôi sẽ đặt lịch theo yêu cầu."
            }

        student_match = re.search(r"sv\d+", prompt_lower)
        student_id = student_match.group(0).upper() if student_match else "SV2026001"
        is_multi_step = "rồi" in prompt_lower or "sau đó" in prompt_lower
        is_booking_request = "đặt lịch" in prompt_lower

        if student_match and "lịch học" in prompt_lower:
            weekday_mapping = {
                "thứ hai": "Thứ Hai",
                "thứ ba": "Thứ Ba",
                "thứ tư": "Thứ Tư",
                "thứ năm": "Thứ Năm",
                "thứ sáu": "Thứ Sáu",
            }
            arguments = {"student_id": student_id}
            for phrase, weekday in weekday_mapping.items():
                if phrase in prompt_lower:
                    arguments["weekday"] = weekday
                    break
            return {
                "type": "tool_call",
                "tool_name": "class_schedule_query",
                "arguments": arguments,
                "thought": f"Người dùng yêu cầu lịch học của {student_id}; tôi sẽ tra cứu lịch học từ tool."
            }

        if student_match and "lịch thi" in prompt_lower:
            course_match = re.search(r"\b[A-Z]{2,}\d{3}\b", prompt.upper())
            arguments = {"student_id": student_id}
            if course_match:
                arguments["course_code"] = course_match.group(0)
            return {
                "type": "tool_call",
                "tool_name": "exam_schedule_query",
                "arguments": arguments,
                "thought": f"Người dùng yêu cầu lịch thi của {student_id}; tôi sẽ tra cứu lịch thi từ tool."
            }
        
        # Mô phỏng nhận diện intent gọi Tool
        if student_match and ("tra cứu" in prompt_lower or is_multi_step):
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": student_id},
                "thought": f"Tôi cần tra cứu hồ sơ của sinh viên {student_id} trước khi xử lý yêu cầu."
            }
        if is_booking_request:
            missing_details = []
            if not student_match:
                missing_details.append("mã sinh viên")
            if not re.search(r"\b\d{1,2}:\d{2}\b", prompt):
                missing_details.append("thời gian hẹn")
            if not re.search(r"(?:pgs\.?\s*ts\.?|ts\.?)", prompt_lower):
                missing_details.append("tên cố vấn")
            if missing_details:
                return {
                    "type": "text",
                    "content": "Để đặt lịch, vui lòng cung cấp " + ", ".join(missing_details) + ".",
                    "thought": "Yêu cầu đặt lịch chưa đủ thông tin bắt buộc nên cần hỏi lại."
                }
            return {
                "type": "tool_call",
                "tool_name": "schedule_appointment",
                "arguments": {"student_id": student_id, "datetime_str": "14:00 15/09/2026", "advisor_name": "PGS.TS Nguyễn Văn A"},
                "thought": f"Người dùng yêu cầu đặt lịch hẹn tư vấn cho sinh viên {student_id}. Tôi sẽ gọi tool schedule_appointment."
            }
        elif student_match or "tra cứu" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "academic_query",
                "arguments": {"student_id": student_id},
                "thought": f"Người dùng muốn tra cứu thông tin học vụ của sinh viên {student_id}. Tôi sẽ gọi tool academic_query."
            }
        else:
            return {
                "type": "text",
                "content": f"[Mock Agent Response]: Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp.",
                "thought": "Câu hỏi chung về quy chế học vụ, trả lời trực tiếp không cần gọi Tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        self.base_url = os.getenv("GEMINI_BASE_URL") or os.getenv("API_BASE_URL") or None

    def _create_client(self):
        from google import genai

        if not self.base_url:
            return genai.Client(api_key=self.api_key)

        from google.genai import types
        return genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(base_url=self.base_url),
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            client = self._create_client()
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, context)
        
        try:
            from google.genai import types

            client = self._create_client()
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            conversation_prompt = prompt
            if context:
                conversation_prompt += "\n\nObservation từ các tool trước đó:\n" + json.dumps(context, ensure_ascii=False)

            response = client.models.generate_content(
                model=self.model_name,
                contents=conversation_prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, context)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self.base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("API_BASE_URL") or None

    def _create_client(self):
        from openai import OpenAI

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            client = self._create_client()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, context)

        try:
            client = self._create_client()

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            conversation_prompt = prompt
            if context:
                conversation_prompt += "\n\nObservation từ các tool trước đó:\n" + json.dumps(context, ensure_ascii=False)
            messages.append({"role": "user", "content": conversation_prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, context)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
