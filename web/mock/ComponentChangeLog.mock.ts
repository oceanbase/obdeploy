// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/:name/component_change/log': (req: Request, res: Response) => {
    res.status(200).send({
      code: 97,
      data: { log: '式特存小理最听集装际切清转该。', offset: 63 },
      msg: '十石却江音三地叫只由张被说而题。',
      success: false,
    });
  },
};
