# scripts/ocr/preprocess/logger.py
class PreprocessingLogger:
    """シンプルなログ管理"""
    
    def __init__(self):
        self.attempt_count = 0
        self.results = []
    
    def log_attempt(self, stage_name: str, found_any_line: bool, found_numeric_like: bool):
        """試行結果のログ"""
        self.attempt_count += 1
        result = {
            "attempt": self.attempt_count,
            "stage": stage_name,
            "found_line": found_any_line,
            "found_numeric": found_numeric_like
        }
        self.results.append(result)
        
        print(f"Attempt {self.attempt_count} ({stage_name}): "
              f"line={found_any_line}, numeric={found_numeric_like}")
    
    def get_summary(self):
        """結果サマリ取得"""
        success = any(r["found_numeric"] for r in self.results)
        return {
            "total_attempts": self.attempt_count,
            "success": success,
            "results": self.results
        }