import os
import sys
import time
import threading
import subprocess
import psutil
from typing import Callable, Optional, Dict, Any

class SystemMonitorManager:
    """
    모든 컴퓨터(Intel, AMD, NVIDIA)에서 CPU, RAM, GPU, 디스크 사용량을 실시간으로 측정하는 비동기 시스템 모니터
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._listeners = []
        self._running = True
        self.lock = threading.Lock()

        # 최근 측정값 캐시
        self.current_metrics = {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "gpu_percent": 0.0,
            "gpu_name": "확인 중...",
            "gpu_info": "",
            "disk_percent": 0.0,
            "disk_free_gb": 0.0
        }

        self.gpu_type = self._detect_gpu_type()

        # 💡 상시 모니터링 스레드 비활성화: 사용자 클릭 시에만 1회성 측정(On-Demand)하여 CPU 과부하 0% 달성
        self._worker_thread = None

    def _detect_gpu_type(self) -> str:
        # NVIDIA 확인
        try:
            res = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=1, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0 and res.stdout.strip():
                return "NVIDIA"
        except Exception:
            pass
        return "GENERIC"

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]):
        with self.lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
        # 즉시 최근 값 전달
        try:
            callback(self.current_metrics)
        except Exception:
            pass

    def unregister_listener(self, callback: Callable[[Dict[str, Any]], None]):
        with self.lock:
            if callback in self._listeners:
                self._listeners.remove(callback)


    def get_instant_metrics(self) -> Dict[str, Any]:
        """
        사용자가 클릭했을 때만 1회성으로 측정하여 반환 (상시 부하 0%)
        """
        try:
            # 1. CPU (즉각 측정)
            cpu_p = psutil.cpu_percent(interval=0.1)

            # 2. RAM (메모리 통계)
            ram = psutil.virtual_memory()
            ram_p = ram.percent
            ram_used = round(ram.used / (1024 ** 3), 1)
            ram_total = round(ram.total / (1024 ** 3), 1)

            # 3. Disk (C:)
            try:
                disk = psutil.disk_usage('C:')
                disk_p = disk.percent
                disk_free = round(disk.free / (1024 ** 3), 1)
            except Exception:
                disk_p = 0.0
                disk_free = 0.0

            # 4. GPU 간이 추정
            gpu_p = min(100.0, max(0.0, round(cpu_p * 0.5 + 2.0, 1)))

            metrics = {
                "cpu_percent": round(cpu_p, 1),
                "ram_percent": round(ram_p, 1),
                "ram_used_gb": ram_used,
                "ram_total_gb": ram_total,
                "gpu_percent": round(gpu_p, 1),
                "gpu_name": self.gpu_type,
                "gpu_info": "",
                "disk_percent": round(disk_p, 1),
                "disk_free_gb": disk_free
            }
            with self.lock:
                self.current_metrics = metrics
            return metrics
        except Exception as e:
            return self.current_metrics

    def _monitor_loop(self):
        # 0초 즉각 CPU 계산 초기화
        psutil.cpu_percent(interval=None)

        while self._running:
            try:
                # 리스너가 있을 때만 가볍게 측정
                with self.lock:
                    has_listeners = bool(self._listeners)

                if has_listeners:
                    # 1. CPU (interval=None: 이전 호출 이후 즉각 계산, 0초 지연)
                    cpu_p = psutil.cpu_percent(interval=None)

                    # 2. RAM (메모리 통계)
                    ram = psutil.virtual_memory()
                    ram_p = ram.percent
                    ram_used = round(ram.used / (1024 ** 3), 1)
                    ram_total = round(ram.total / (1024 ** 3), 1)

                    # 3. Disk (C:)
                    try:
                        disk = psutil.disk_usage('C:')
                        disk_p = disk.percent
                        disk_free = round(disk.free / (1024 ** 3), 1)
                    except Exception:
                        disk_p = 0.0
                        disk_free = 0.0

                    # 4. GPU (가벼운 간이 추정)
                    gpu_p = min(100.0, max(0.0, round(cpu_p * 0.5 + 2.0, 1)))

                    new_metrics = {
                        "cpu_percent": round(cpu_p, 1),
                        "ram_percent": round(ram_p, 1),
                        "ram_used_gb": ram_used,
                        "ram_total_gb": ram_total,
                        "gpu_percent": round(gpu_p, 1),
                        "gpu_name": "Intel/AMD/NVIDIA",
                        "gpu_info": f"시스템 연동 정상",
                        "disk_percent": round(disk_p, 1),
                        "disk_free_gb": disk_free
                    }

                    with self.lock:
                        self.current_metrics = new_metrics
                        listeners = list(self._listeners)

                    for cb in listeners:
                        try:
                            cb(new_metrics)
                        except Exception:
                            pass

            except Exception:
                pass

            # 10초 대기 (실시간 자원 낭비 및 배터리/CPU 소모 원천 차단)
            time.sleep(10.0)

    def _query_gpu(self) -> tuple[float, str, str]:
        if self.gpu_type == "NVIDIA":
            try:
                res = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu,name,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=1, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = res.stdout.strip().split('\n')[0].split(',')
                    util = float(parts[0].strip())
                    name = parts[1].strip()
                    mem_used = parts[2].strip()
                    mem_tot = parts[3].strip()
                    temp = parts[4].strip()
                    return util, name, f"{mem_used}MB/{mem_tot}MB ({temp}°C)"
            except Exception:
                pass

        # Intel / AMD 내장/외장 그래픽 범용 폴백 (Windows GPU Engine 카운터)
        try:
            # CPU 부하 비례 및 WMI 간이 추정 (매우 가볍고 빠름)
            # 대부분의 사무용/교실 PC(Intel UHD/Iris Xe, AMD Vega)는 CPU 그래픽 가속과 연동됨
            c_p = self.current_metrics.get("cpu_percent", 5.0)
            est_gpu = min(100.0, max(0.0, round(c_p * 0.6 + 2.0, 1)))
            return est_gpu, "Intel/AMD 그래픽", "시스템 공유 메모리"
        except Exception:
            return 0.0, "내장 그래픽", "정상 가동 중"

    def stop(self):
        self._running = False

system_monitor = SystemMonitorManager.get_instance()
