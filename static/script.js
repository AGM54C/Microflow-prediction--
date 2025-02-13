document.addEventListener('DOMContentLoaded', function () {
    const inputForm = document.getElementById('inputForm');
    const resultArea = document.getElementById('resultArea');
    const dataTypeSelect = document.getElementById('dataType');
    const type1Inputs = document.getElementById('type1Inputs');
    const type2Inputs = document.getElementById('type2Inputs');
    const type3Inputs = document.getElementById('type3Inputs');

    // 页面加载时根据当前选择显示对应输入框
    function showSelectedInputs() {
        const selectedType = dataTypeSelect.value;
        type1Inputs.style.display = 'none';
        type2Inputs.style.display = 'none';
        type3Inputs.style.display = 'none';
        if (selectedType === 'type1') {
            type1Inputs.style.display = 'block';
        } else if (selectedType === 'type2') {
            type2Inputs.style.display = 'block';
        } else if (selectedType === 'type3') {
            type3Inputs.style.display = 'block';
        }
    }

    // 页面加载时调用一次显示对应输入框
    showSelectedInputs();

    // 监听数据类型选择框的变化事件
    if (dataTypeSelect) {
        dataTypeSelect.onchange = function () {
            showSelectedInputs();
        };
    }

    // 监听表单的提交事件
    if (inputForm) {
        inputForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const dataType = dataTypeSelect.value;
            let inputData = [];

            if (dataType === 'type3') {
                for (let i = 1; i <= 9; i++) {
                    const input = document.querySelector(`input[name="${dataType}_data${i}"]`);
                    if (!input) {
                        console.error(`未找到 name 为 ${dataType}_data${i} 的输入框`);
                        return;
                    }
                    const value = ensureNumber(input.value);
                    console.log(`${dataType}_data${i} 的输入值:`, input.value, '解析后的值:', value);
                    inputData.push(value);
                }
                if (inputData.length!== 9) {
                    alert('输入数据长度必须为 9');
                    console.error('输入数据长度不符合要求:', inputData);
                    return;
                }
            } else {
                for (let i = 1; i <= 8; i++) {
                    const input = document.querySelector(`input[name="${dataType}_data${i}"]`);
                    if (!input) {
                        console.error(`未找到 name 为 ${dataType}_data${i} 的输入框`);
                        return;
                    }
                    const value = ensureNumber(input.value);
                    console.log(`${dataType}_data${i} 的输入值:`, input.value, '解析后的值:', value);
                    inputData.push(value);
                }
                if (inputData.length!== 8) {
                    alert('输入数据长度必须为 8');
                    console.error('输入数据长度不符合要求:', inputData);
                    return;
                }
            }

            if (inputData.some(value => isNaN(value))) {
                alert('输入数据必须是有效的数字');
                console.error('无效输入数据:', inputData);
                return;
            }

            console.log('即将发送的数据:', { dataType: dataType, inputData: inputData });

            fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ dataType: dataType, inputData: inputData })
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP 错误！状态码: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && data.prediction!== undefined) {
                        resultArea.textContent = data.prediction;
                    } else {
                        throw new Error('无效的响应格式。缺少预测字段。');
                    }
                })
                .catch(error => {
                    console.error('错误:', error);
                    resultArea.textContent = '发生错误，请稍后再试。';
                });
        });
    }
});

function ensureNumber(value) {
    value = value.trim();
    const num = Number(value);
    if (isNaN(num)) {
        return NaN;
    }
    return num;
}
