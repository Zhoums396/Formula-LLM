/**
 * 环境变量加载脚本
 */

const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// 加载环境变量
function loadEnv() {
  const envPath = path.join(__dirname, '../.env');
  const examplePath = path.join(__dirname, '../.env.example');
  
  // 检查.env文件是否存在
  if (!fs.existsSync(envPath)) {
    // 如果不存在，但.env.example存在，则复制它
    if (fs.existsSync(examplePath)) {
      fs.copyFileSync(examplePath, envPath);
      console.log('已创建.env文件，请编辑它以设置您的API密钥和其他配置。');
    } else {
      console.warn('未找到.env文件或.env.example文件，某些功能可能无法正常工作。');
    }
  }
  
  // 加载.env文件
  const result = dotenv.config({ path: envPath });
  
  if (result.error) {
    console.warn(`加载.env文件时出错: ${result.error.message}`);
    return false;
  }
  
  return true;
}

module.exports = { loadEnv }; 
