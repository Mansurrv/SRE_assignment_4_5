output "public_ip" {
  description = "Public IP of the VM."
  value       = aws_instance.vm.public_ip
}

output "instance_id" {
  description = "EC2 instance id."
  value       = aws_instance.vm.id
}

