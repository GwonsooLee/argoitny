variable "sg_variables" {
  default = {
    ec2 = {
      tags = {
        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-ec2-sg"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        }
      }
    }

    external_lb = {
      tags = {
        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-external-lb-sg"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        }

      }
    }

    internal_lb = {
      tags = {
        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-internal-lb-sg"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        }
     }
    }  


  }
}
