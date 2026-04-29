# Итоговый отчет (SRE Assignments 4/5)

Дата: **заполните**  
Автор: **заполните**  

## 1) Отчет по инфраструктуре (Terraform)

### 1.1 Файлы Terraform (.tf)

#### `main.tf`
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "ssh" {
  key_name   = var.ssh_key_name
  public_key = file(var.ssh_public_key_path)
}

resource "aws_security_group" "vm" {
  name        = "${var.project_name}-sg"
  description = "Allow SSH, HTTP, app and Prometheus ports"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_ingress_cidrs
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App (3000)"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Prometheus (9090)"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "vm" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.vm.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.ssh.key_name
}
```

#### `variables.tf`
```hcl
variable "project_name" {
  type        = string
  description = "Name prefix for resources."
  default     = "sre-assignment-5"
}

variable "region" {
  type        = string
  description = "AWS region."
  default     = "us-east-1"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.micro"
}

variable "ssh_key_name" {
  type        = string
  description = "Name of the EC2 key pair to create/use."
  default     = "sre-assignment-5-key"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to your SSH public key (e.g. ~/.ssh/id_rsa.pub)."
}
```

#### `outputs.tf`
```hcl
output "public_ip" {
  description = "Public IP of the VM."
  value       = aws_instance.vm.public_ip
}

output "instance_id" {
  description = "EC2 instance id."
  value       = aws_instance.vm.id
}
```

### 1.2 Скриншот terraform apply

Вставьте скриншот терминала с успешным `terraform apply` (где видны `instance_id` и `public_ip`).

Файл: `report/screenshots/terraform-apply.png`

## 2) Incident Report

### Severity
- **Severity:** High (для учебного задания)

### Краткое описание
- Во время инцидента `Order Service` начал отдавать ошибки 5xx при создании заказов.
- Детекция была выполнена через Grafana (рост 5xx / падение успешных заказов).

### Timeline (укажите ваш часовой пояс, напр. Asia/Almaty)
- 07:30 — инцидент начался (внесена ошибочная конфигурация `order-service`, запросы `POST /orders` начали возвращать 5xx).
- 07:33 — обнаружено в Grafana (рост `Order Service 5xx`, падение успешных `POST /orders 2xx`).
- 07:45 — исправлено (конфиг откатан, `order-service` перезапущен, 5xx пошли вниз).

### Root Cause
- Ошибка в конфигурации `Order Service` (неверный URL/host зависимости), что приводило к ошибкам при обработке `POST /orders`.

## 3) Postmortem (что сделать, чтобы не повторилось)

Предложения:
- Добавить автоматические проверки (CI) для конфигурации окружения (валидность `DATABASE_URL`, `*_SERVICE_URL`).
- Добавить алерты в Grafana/Prometheus (например, `5xx > 0` в течение 1–5 минут).
- Уточнить healthchecks: отдельный endpoint типа `/ready` проверяет доступность зависимостей.
- Ограничить ручные изменения конфигов и использовать `.env`/secrets менеджмент.

## 4) Скриншоты (обязательно)

### 4.1 Список контейнеров (docker ps)
Сделайте скриншот/вставку вывода `docker ps`:
- Скриншот: `report/screenshots/docker-ps.png`
- Или текстовый листинг: `report/docker-ps.txt`

### 4.2 Дашборд Grafana
Скриншот дашборда с графиками (во время инцидента):
- `report/screenshots/grafana-incident.png`

### 4.3 Работающий веб-интерфейс
Скриншот страницы `http://localhost:8080`:
- `report/screenshots/web-ui.png`

## Экспорт в PDF

Самый простой способ: открыть `report/REPORT.md` в IDE или браузере и **Print → Save as PDF**.
