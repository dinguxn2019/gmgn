from flask import Flask, request, jsonify, Response
import subprocess
from flask_cors import CORS
import os
import json
import time
from queue import Queue
from threading import Thread

app = Flask(__name__)
CORS(app)

def process_address(address, queue):
    """处理单个地址并将结果放入队列"""
    try:
        command = f'python gmgn_get_info.py -i {address}'
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0 and stdout.strip():
            # 假设输出格式为: address,winRate,transactions,profit,balance
            parts = stdout.strip().split(',')
            if len(parts) >= 5:
                result = {
                    'address': parts[0].strip(),
                    'winRate': parts[1].strip(),
                    'transactions': parts[2].strip(),
                    'profit': parts[3].strip(),
                    'balance': parts[4].strip()
                }
                queue.put(('result', result))
            else:
                queue.put(('error', f'Invalid data format for address {address}'))
        else:
            queue.put(('error', f'Error processing address {address}: {stderr}'))
    except Exception as e:
        queue.put(('error', f'Exception processing address {address}: {str(e)}'))

@app.route('/get-info-stream')
def get_info_stream():
    """SSE endpoint for real-time updates"""
    def generate():
        addresses = request.args.get('addresses', '').split()
        if not addresses:
            yield 'data: {"error": "No addresses provided"}\n\n'
            return

        queue = Queue()
        threads = []

        # 启动所有处理线程
        for address in addresses:
            thread = Thread(target=process_address, args=(address, queue))
            thread.start()
            threads.append(thread)

        # 等待结果并发送
        completed = 0
        while completed < len(addresses):
            try:
                event_type, data = queue.get(timeout=1)
                if event_type == 'result':
                    yield f'event: result\ndata: {json.dumps(data)}\n\n'
                elif event_type == 'error':
                    yield f'event: error\ndata: {json.dumps({"error": data})}\n\n'
                completed += 1
            except:
                # 超时继续等待
                continue

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 发送完成事件
        yield 'event: complete\ndata: {"status": "complete"}\n\n'

    return Response(generate(), mimetype='text/event-stream')

@app.route('/execute', methods=['POST'])
def execute_command():
    try:
        data = request.json
        contract_address = data.get('contractAddress')
        address_count = data.get('addressCount')
        
        if not contract_address or not address_count:
            return jsonify({
                'success': False,
                'error': 'ContractAddress and addressCount are required'
            }), 400

        # 构建命令
        command = f'python gmgn_get_url.py -i {contract_address} -n {address_count}'
        print(f"Executing command: {command}")  # 打印执行的命令
        
        # 执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',  # 使用 UTF-8 编码
            text=True
        )
        
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        print(f"Command return code: {return_code}")
        print(f"Raw stdout: {stdout}")  # 打印原始输出
        print(f"Raw stderr: {stderr}")  # 打印原始错误
        
        # 处理输出，忽略日志信息
        actual_stderr = '\n'.join([line for line in (stderr or '').split('\n') if line and not line.startswith('2024-')])
        
        # 如果进程返回非零状态码
        if return_code != 0:
            error_msg = actual_stderr or f"Command failed with return code {return_code}"
            print(f"Process failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'command': command,
                'return_code': return_code
            }), 500
            
        # 处理输出，忽略空行
        actual_stdout = '\n'.join([line for line in (stdout or '').split('\n') if line.strip()])
            
        # 如果没有实际输出
        if not actual_stdout:
            print("Command executed but produced no output")
            return jsonify({
                'success': False,
                'error': '命令执行成功但没有输出',
                'command': command,
                'return_code': return_code
            }), 500

        print(f"Actual command output: {actual_stdout}")  # 打印实际命令输出
        
        return jsonify({
            'success': True,
            'stdout': actual_stdout,
            'stderr': stderr,  # 保留原始stderr以供调试
            'output': actual_stdout,  # 为了保持与前端代码兼容
            'command': command,  # 返回执行的命令，方便调试
            'return_code': return_code
        })
    except Exception as e:
        print(f"Exception occurred: {str(e)}")  # 打印异常信息
        return jsonify({
            'success': False,
            'error': str(e),
            'command': command if 'command' in locals() else None
        }), 500

@app.route('/get-info', methods=['POST'])
def get_info():
    try:
        data = request.json
        address = data.get('address')
        if not address:
            return jsonify({
                'success': False,
                'error': 'Address parameter is required'
            }), 400
            
        command = f'python gmgn_get_info.py -i {address}'
        print(f"Executing command: {command}")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 设置环境变量强制使用UTF-8
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 使用UTF-8编码执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=current_dir,
            env=env,
            encoding='utf-8',
            text=True
        )
        
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        print(f"Command return code: {return_code}")
        print(f"Raw stdout: {stdout}")
        print(f"Raw stderr: {stderr}")
        print(f"Working directory: {current_dir}")
        
        # 处理输出，忽略空行
        actual_stdout = '\n'.join([line for line in (stdout or '').split('\n') if line.strip()])
        actual_stderr = '\n'.join([line for line in (stderr or '').split('\n') if line.strip()])
        
        if return_code != 0:
            error_msg = actual_stderr or f"Command failed with return code {return_code}"
            print(f"Process failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'command': command,
                'return_code': return_code,
                'working_dir': current_dir
            }), 500
        
        if not actual_stdout:
            print("Command executed but produced no output")
            return jsonify({
                'success': False,
                'error': '命令执行成功但没有输出',
                'command': command,
                'return_code': return_code,
                'working_dir': current_dir
            }), 500
        
        return jsonify({
            'success': True,
            'stdout': actual_stdout,
            'stderr': actual_stderr,
            'command': command,
            'return_code': return_code,
            'working_dir': current_dir
        })
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'command': command if 'command' in locals() else None
        }), 500

if __name__ == '__main__':
    app.run(port=5000) 