# Route53 Record for Primary DB endpoint
resource "aws_route53_record" "algoitny_db" {
  zone_id = data.terraform_remote_state.vpc.outputs.route53_internal_zone_id
  name    = "algoitny-db.${data.terraform_remote_state.vpc.outputs.route53_internal_domain}"
  type    = "CNAME"
  ttl     = 60
  records = [var.algoitny_aurora_endpoint]
}


# Route53 Record for Replica DB endpoint
resource "aws_route53_record" "algoitny_db_replica" {
  zone_id = data.terraform_remote_state.vpc.outputs.route53_internal_zone_id
  name    = "algoitny-db-replica.${data.terraform_remote_state.vpc.outputs.route53_internal_domain}"
  type    = "CNAME"
  ttl     = 60
  records = [var.algoitny_aurora_reader_endpoint]
}
