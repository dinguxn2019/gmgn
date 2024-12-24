document.addEventListener('DOMContentLoaded', function() {
    const fetchButton = document.querySelector('.fetch-top-holders');
    const addressesList = document.getElementById('addressesList');
    const copyAllBtn = document.querySelector('.copy-all-btn');
    const downloadCsvBtn = document.getElementById('download-csv');
    const resultsTable = document.querySelector('.output-section table tbody');
    const clearButton = document.querySelector('.clear-results');
    const walletAddressesTextarea = document.getElementById('wallet-addresses');
    const startQueryButton = document.querySelector('.start-query');

    // 清除按钮功能
    clearButton.addEventListener('click', function() {
        walletAddressesTextarea.value = '';
    });

    // 检查output-section-u中的内容并更新下载按钮状态
    function updateDownloadButtonState() {
        const outputTable = document.querySelector('.output-section-u table tbody');
        const rows = outputTable.getElementsByTagName('tr');
        const hasValidData = Array.from(rows).some(row => {
            // 检查行是否包含实际数据（不是错误消息或"暂无数据"）
            const cells = row.getElementsByTagName('td');
            return cells.length > 1 || (cells.length === 1 && !cells[0].textContent.includes('暂无数据') && !cells[0].textContent.includes('查询出错'));
        });
        downloadCsvBtn.disabled = !hasValidData;
    }

    // 在数据更新后调用状态更新函数
    const observer = new MutationObserver(function(mutations) {
        updateDownloadButtonState();
    });

    // 监视output-section-u表格内容的变化
    const outputTable = document.querySelector('.output-section-u table tbody');
    observer.observe(outputTable, { childList: true, subtree: true });

    // 初始化按钮状态
    updateDownloadButtonState();

    // 下载CSV文件功能
    downloadCsvBtn.addEventListener('click', function() {
        if (!this.disabled) {
            window.location.href = 'results.csv';
        }
    });

    // 复制所有地址的功能
    copyAllBtn.addEventListener('click', function() {
        const addresses = Array.from(addressesList.getElementsByTagName('tr'))
            .map(tr => tr.children[1]?.textContent.trim())
            .filter(address => address)
            .join('\n');
        
        navigator.clipboard.writeText(addresses).then(() => {
            const originalText = this.innerHTML;
            this.innerHTML = '已复制！';
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        }).catch(err => {
            console.error('复制失败:', err);
            alert('复制失败，请手动复制');
        });
    });

    // 获取持有者功能
    fetchButton.addEventListener('click', async function() {
        this.disabled = true;
        
        // 从输入框获取合约地址和地址数量
        const contractAddress = document.getElementById('contract-address').value;
        const addressCount = document.getElementById('address-count').value;

        // 验证合约地址是否已输入
        if (!contractAddress) {
            alert('请输入合约地址');
            this.disabled = false;
            return;
        }

        // 验证地址数量是否有效
        if (!addressCount || addressCount < 1 || addressCount > 100) {
            alert('请输入有效的地址数量（1-100）');
            this.disabled = false;
            return;
        }

        // 显示加载状态
        this.innerHTML = '正在获取数据...';
        addressesList.innerHTML = '<tr><td colspan="2" class="loading">正在获取数据，请稍候...</td></tr>';

        try {
            const response = await fetch('http://localhost:5000/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    contractAddress: contractAddress.trim(),
                    addressCount: parseInt(addressCount)
                })
            });

            let errorMessage = '';
            if (!response.ok) {
                const errorData = await response.text();
                try {
                    const jsonError = JSON.parse(errorData);
                    errorMessage = jsonError.error || jsonError.message || '未知错误';
                } catch {
                    errorMessage = errorData || `服务器错误 (${response.status})`;
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            addressesList.innerHTML = '';
            
            if (!data.success) {
                throw new Error(data.error || '获取数据失败');
            }

            if (data.output) {
                const addresses = data.output.split('\n')
                    .filter(line => line.trim())
                    .map((address, index) => `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${address.trim()}</td>
                        </tr>
                    `);
                
                if (addresses.length > 0) {
                    addressesList.innerHTML = addresses.join('');
                } else {
                    addressesList.innerHTML = '<tr><td colspan="2">未找到地址数据</td></tr>';
                }
            } else {
                addressesList.innerHTML = '<tr><td colspan="2">未找到地址数据</td></tr>';
            }
        } catch (error) {
            console.error('Error:', error);
            addressesList.innerHTML = `
                <tr>
                    <td colspan="2" style="color: red;">
                        <div>请求失败:</div>
                        <div>${error.message}</div>
                        <div style="font-size: 0.9em; margin-top: 8px;">
                            请检查：<br>
                            1. 合约地址是否正确<br>
                            2. 后端服务是否正常运行<br>
                            3. 网络连接是否正常
                        </div>
                    </td>
                </tr>`;
        } finally {
            this.disabled = false;
            this.innerHTML = '提取持有者';
        }
    });

    // 开始查询按钮功能
    startQueryButton.addEventListener('click', async function() {
        try {
            // 检查钱包地址是否为空
            const addresses = walletAddressesTextarea.value.trim();
            if (!addresses) {
                alert('请输入钱包地址');
                return;
            }

            // 将多行地址转换为数组
            const addressList = addresses.split('\n')
                .map(addr => addr.trim())
                .filter(addr => addr);

            this.disabled = true;

            // 获取结果表格的tbody并显示加载状态
            const resultsTableBody = document.querySelector('.output-section-u table tbody');
            resultsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">正在查询中...</td></tr>';

            // 清空表格准备接收新数据
            resultsTableBody.innerHTML = '';
            
            // 创建进度显示行
            const progressRow = document.createElement('tr');
            progressRow.innerHTML = `<td colspan="5" style="text-align: center;">已处理: <span id="processed-count">0</span>/${addressList.length} 个地址</td>`;
            resultsTableBody.appendChild(progressRow);

            // 如果存在之前的 EventSource，���闭它
            if (window.currentEventSource) {
                window.currentEventSource.close();
            }

            // 尝试连接后端
            let retryCount = 0;
            const maxRetries = 3;
            let response;

            while (retryCount < maxRetries) {
                try {
                    response = await fetch('http://localhost:5000/get-info', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({
                            address: addressList.join(' ')
                        })
                    });

                    if (response.ok) {
                        break;
                    }

                    retryCount++;
                    if (retryCount < maxRetries) {
                        await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
                    }
                } catch (error) {
                    console.error(`Attempt ${retryCount + 1} failed:`, error);
                    retryCount++;
                    if (retryCount < maxRetries) {
                        await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
                    } else {
                        throw new Error('无法连接到服务器，请检查服务器是否正常运行');
                    }
                }
            }

            if (!response || !response.ok) {
                throw new Error(`服务器响应错误: ${response ? response.status : '无响应'}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || '查询失败');
            }

            // 处理返回的数据
            if (data.stdout) {
                const lines = data.stdout.split('\n').filter(line => line.trim());
                
                // 移除进度行
                progressRow.remove();

                if (lines.length === 0) {
                    resultsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">暂无数据</td></tr>';
                    return;
                }

                lines.forEach(line => {
                    const parts = line.split(',');
                    if (parts.length >= 5) {
                        const row = document.createElement('tr');
                        
                        // 钱包地址
                        const addressCell = document.createElement('td');
                        addressCell.textContent = parts[0].trim();
                        row.appendChild(addressCell);
                        
                        // 胜率
                        const winRateCell = document.createElement('td');
                        winRateCell.textContent = parts[1].trim();
                        row.appendChild(winRateCell);
                        
                        // 7D交易数
                        const transactionCell = document.createElement('td');
                        transactionCell.textContent = parts[2].trim();
                        row.appendChild(transactionCell);
                        
                        // 最近7D盈亏
                        const profitCell = document.createElement('td');
                        profitCell.textContent = parts[3].trim();
                        row.appendChild(profitCell);
                        
                        // SOL余额
                        const balanceCell = document.createElement('td');
                        balanceCell.textContent = parts[4].trim();
                        row.appendChild(balanceCell);

                        resultsTableBody.appendChild(row);
                    }
                });
            } else {
                resultsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">暂无数据</td></tr>';
            }

        } catch (error) {
            console.error('Error:', error);
            const resultsTableBody = document.querySelector('.output-section-u table tbody');
            resultsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" style="color: red; text-align: center;">
                        <div>查询失败:</div>
                        <div>${error.message}</div>
                        <div style="font-size: 0.9em; margin-top: 8px;">
                            请检查：<br>
                            1. 后端服务是否正常运行（http://localhost:5000）<br>
                            2. 网络连接是否正常<br>
                            3. 输入的地址格式是否正确
                        </div>
                    </td>
                </tr>`;
        } finally {
            this.disabled = false;
        }
    });
}); 