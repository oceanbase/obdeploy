// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/component_change/:name/del': (req: Request, res: Response) => {
    res.status(200).send({
      code: 66,
      data: { log: '来如年标感精元近数转已应于。', offset: 84 },
      msg: '术号产小定做热社支会需者。',
      success: false,
    });
  },
};
