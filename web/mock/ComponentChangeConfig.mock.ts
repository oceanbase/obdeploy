// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/component_change/:name/deployment': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 64, data: null, msg: '影酸点形比全口织解一消等选影八月。', success: false });
  },
};
