// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/info': (req: Request, res: Response) => {
    res.status(200).send({
      code: 65,
      data: { user: '对员住作列时除老量情三增太声。' },
      msg: '铁众百级细省于论斗也我或。',
      success: true,
    });
  },
};
