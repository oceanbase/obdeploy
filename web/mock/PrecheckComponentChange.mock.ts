// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/component_change/:name/precheck': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 90, data: null, msg: '书入他积数历次条把是院表名。', success: false });
  },
};
