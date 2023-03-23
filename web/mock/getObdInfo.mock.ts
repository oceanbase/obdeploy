// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/info': (req: Request, res: Response) => {
    res.status(200).send({
      code: 74,
      data: { user: '没点价种但想军约张界委气建张。' },
      msg: '老老县说局建东通面水市论面月就命八光。',
      success: false,
    });
  },
};
