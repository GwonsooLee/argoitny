variable "r53_variables" {
  default = {
    prod = {
      star_testcase_run_acm_arn_useast1      = "arn:aws:acm:us-east-1:442863828268:certificate/7475d275-36c8-415d-a62e-38211bcdfabc"
      star_testcase_run_acm_arn_apnortheast2 = "arn:aws:acm:ap-northeast-2:442863828268:certificate/3ee9eb5f-fa48-4c2c-b9bf-f5ee2426dc9b"
      testcase_run_zone_id                   = "Z06967682IK2O4YNOHOR7"
    }
  }
}

