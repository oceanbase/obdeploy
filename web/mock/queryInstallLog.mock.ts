// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/install/log': (
    req: Request,
    res: Response,
  ) => {
    res.status(200).send({
      code: 62,
      data: { log: '眼约派如变住当或合放科加。', offset: 94 },
      msg: '阶记很温细回百几则酸声生族。',
      success: true,
    });
  },
};
