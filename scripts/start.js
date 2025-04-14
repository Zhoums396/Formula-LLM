#!/usr/bin/env node

/**
 * 公式识别与问答系统启动脚本
 * 封装Python服务，提供友好的命令行界面
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');
const dotenv = require('dotenv');

// 加载环境变量
try {
  const envPath = path.join(__dirname, '../.env');
  const examplePath = path.join(__dirname, '../.env.example');
  
  // 检查.env文件是否存在
  if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) {
    fs.copyFileSync(examplePath, envPath);
    console.log(chalk.yellow('已创建.env文件，使用默认配置'));
  }
  
  dotenv.config();
} catch (error) {
  console.log(chalk.yellow('加载环境变量失败，将使用默认配置'));
}

// 检查Python环境
async function checkPythonEnvironment() {
  console.log(chalk.blue('🔍 正在检查Python环境...'));
  
  try {
    const python = spawn('python', ['--version']);
    
    return new Promise((resolve) => {
      python.on('close', (code) => {
        if (code === 0) {
          console.log(chalk.green('✅ Python环境正常'));
          resolve(true);
        } else {
          console.log(chalk.red('❌ Python环境检查失败，请确保已安装Python'));
          resolve(false);
        }
      });
    });
  } catch (error) {
    console.log(chalk.red(`❌ 无法启动Python: ${error.message}`));
    return false;
  }
}

// 检查依赖项
async function checkDependencies() {
  console.log(chalk.blue('🔍 正在检查依赖项...'));
  
  // 检查知识库目录
  if (!fs.existsSync(path.join(__dirname, '../knowledge_base'))) {
    console.log(chalk.yellow('⚠️ 知识库目录不存在，将自动创建'));
    fs.mkdirSync(path.join(__dirname, '../knowledge_base'));
  }
  
  // 检查图像目录
  if (!fs.existsSync(path.join(__dirname, '../images'))) {
    console.log(chalk.yellow('⚠️ 图像目录不存在，将自动创建'));
    fs.mkdirSync(path.join(__dirname, '../images'));
  }
  
  console.log(chalk.green('✅ 依赖项检查完成'));
  return true;
}

// 启动应用程序
async function startApp() {
  console.log(chalk.blue('\n🚀 正在启动公式识别与问答系统...'));
  
  // 使用默认配置，无需用户输入
  const options = {
    port: 7864,
    host: 'localhost',
    inbrowser: true,
    share: false
  };
  
  const args = [
    'pipe.py',
    '--server-port', options.port.toString(),
    '--server-name', options.host
  ];
  
  if (options.inbrowser) {
    args.push('--inbrowser');
  }
  
  if (options.share) {
    args.push('--share');
  }
  
  console.log(chalk.green(`✅ 服务将在 http://${options.host}:${options.port} 上启动`));
  
  const pythonProcess = spawn('python', args, {
    stdio: 'inherit',
    cwd: path.join(__dirname, '..')
  });
  
  pythonProcess.on('error', (error) => {
    console.log(chalk.red(`\n❌ 启动失败: ${error.message}`));
  });
  
  // 处理退出信号
  process.on('SIGINT', () => {
    console.log(chalk.yellow('\n\n正在关闭服务...'));
    pythonProcess.kill('SIGINT');
  });
  
  process.on('SIGTERM', () => {
    console.log(chalk.yellow('\n\n正在关闭服务...'));
    pythonProcess.kill('SIGTERM');
  });
  
  return new Promise((resolve) => {
    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.log(chalk.red(`\n❌ 程序异常退出，退出码: ${code}`));
      }
      resolve();
    });
  });
}

// 主函数
async function main() {
  console.log(chalk.cyan('\n================================================'));
  console.log(chalk.cyan('       📖 公式识别与问答系统启动工具'));
  console.log(chalk.cyan('================================================\n'));
  
  // 检查环境
  const pythonOk = await checkPythonEnvironment();
  if (!pythonOk) {
    process.exit(1);
  }
  
  const dependenciesOk = await checkDependencies();
  if (!dependenciesOk) {
    process.exit(1);
  }
  
  // 直接启动应用，不询问配置
  await startApp();
}

// 运行主函数
main().catch(error => {
  console.error(chalk.red(`\n❌ 发生错误: ${error.message}`));
  process.exit(1);
}); 