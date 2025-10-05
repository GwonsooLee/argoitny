#######
## - It is better to use name of output with certain rules.
## - Example is like this
## 
## Rule : `aws_kms_key_<env>_<region>_<key_name>_arn`
## 
#######
output "aws_kms_key_prod_apne2_algoitny_arn" {
  description = "Key for deployment"
  value       = aws_kms_key.algoitny.arn
}
