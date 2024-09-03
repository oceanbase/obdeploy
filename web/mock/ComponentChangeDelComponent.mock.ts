// @ts-ignore
import { Request, Response } from 'express';

export default {
  'DELETE /api/v1/component_change/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 72, data: null, msg: '研点更压定置与计这民品至产。', success: true });
  },
};
