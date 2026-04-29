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

variable "ssh_ingress_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to SSH (22) into the VM."
  default     = ["0.0.0.0/0"]
}

