variable "lb_variables" {
  default = {

    target_group_slow_start = {
      zteapne2 = 0
    }

    target_group_deregistration_delay = {
      zteapne2 = 60
    }

    external_lb = {
      tags = {

        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-external-lb"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        },
      }
    }

    external_lb_tg = {
      tags = {
        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-external-tg"
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
          Name    = "algoitnyapi-zte_apnortheast2-internal-lb"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        }
      }
    }

    internal_lb_tg = {
      tags = {
        zteapne2 = {
          Name    = "algoitnyapi-zte_apnortheast2-internal-tg"
          app     = "algoitnyapi"
          project = "algoitnyapi"
          env     = "prod"
          stack   = "zte_apnortheast2"
        }
      }
    }

  }
}
