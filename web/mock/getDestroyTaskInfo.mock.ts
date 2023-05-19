// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/destroy': (req: Request, res: Response) => {
    res.status(200).send({
      code: 60,
      data: {
        total: 99,
        finished: 68,
        current: '军积书常次又动究商具却合去式比叫问里。',
        status: null,
        msg: '理持府形东但音果适联来具统布设。',
        info: [
          {
            component: '解列定处格油便县老上斯目期调。',
            status: null,
            result: null,
          },
          {
            component: '原当精带件状以九头料局风定委习起。',
            status: null,
            result: null,
          },
        ],
      },
      msg: '酸因身是问术走养目消存信共。',
      success: true,
    });
  },
  'GET /api/v1/deployments_test': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 90,
        data: null,
        msg: '东较合比参除容术人研半做信。',
        success: true,
      });
  },
};
